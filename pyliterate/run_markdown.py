#!/usr/bin/env python3

# Copyright 2015 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Rewrites a Markdown file by running the Python code embedded within it.

Parses the Markdown file passed as the first command-line argument. Looks for
code blocks like this:

```python
print('Hello world')
```

Runs the code top-to-bottom in the file. When a non-Python block like
this is found:

```
Output goes here
```

All of the prior Python blocks are combined together, run, and their combined
output is inserted. Not every Python block needs to have an output block, but
every output block needs at least one preceeding Python block to produce output.

Python blocks do not have to be stand-alone code blocks. A single class or
function definition can be interleaved with text. For example, this is legal:

```python
def multiply(a, b):
```

And the body is:

```python
    return a * b
```
"""

import argparse
import ast
import logging
logging.getLogger().setLevel(logging.DEBUG)
import io
import os
import pdb
import pprint
import pydoc
import random
import re
import signal
import subprocess
import sys
from time import tzset
import traceback


REAL_PRINT = print
REAL_PPRINT = pprint.pprint


class Flags(object):
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description='Rewrites a Markdown file by running the Python '
                        'code embedded within it.')
        self.parser.add_argument(
            '--overwrite',
            action='store_true',
            default=False,
            help='Overwrite the file in-place if its contents ran '
                 'successfully.')
        self.parser.add_argument(
            '--timeout_seconds',
            action='store',
            default=5,
            type=float,
            help='Kill the process with an error if the Python code in the '
                 'Markdown file hasn\'t finished executing in this time.')
        self.parser.add_argument(
            'path',
            action='store',
            default=None,
            nargs='+',
            help='Paths to the Markdown files to process.')
        self.parser.add_argument(
            '--root_dir',
            action='store',
            default='.',
            type=str,
            help='Path to the root directory of the book. Used to resolve '
                 '"python-include:" blocks in the source Markdown.')

    def parse(self):
        self.parser.parse_args(namespace=self)


FLAGS = Flags()


class MarkdownExecError(Exception):
    pass


class WrappedException(Exception):
    def __init__(self, output=None):
        super().__init__()
        self.output = output


def exec_source(path, source, context, raise_exceptions=False):
    output = io.StringIO()
    logging_handler = logging.StreamHandler(stream=output)

    def my_print(*args, **kwargs):
        kwargs['file'] = output
        REAL_PRINT(*args, **kwargs)

    def my_pprint(*args, **kwargs):
        kwargs['stream'] = output
        kwargs['width'] = 65  # Max width of monospace code lines in Word
        REAL_PPRINT(*args, **kwargs)

    def my_debug(*args, **kwargs):
        kwargs['file'] = sys.stderr
        REAL_PRINT(*args, **kwargs)

    def my_help(*args, **kwargs):
        helper = pydoc.Helper(output=output)
        return helper(*args, **kwargs)

    def my_pdb():
        # Clear any alarm clocks since we're going interactive.
        signal.alarm(0)

        p = pdb.Pdb(stdin=sys.stdin, stdout=sys.stderr)
        p.use_rawinput = True
        return p

    context['print'] = my_print
    context['pprint'] = my_pprint
    context['debug'] = my_debug
    context['help'] = my_help
    context['Pdb'] = my_pdb
    context['STDOUT'] = output
    logging.getLogger().addHandler(logging_handler)
    try:
        node = ast.parse(source, path)
        code = compile(node, path, 'exec')
        exec(code, context, context)
    except Exception as e:
        # Restore the print functions for other code in this module.
        context['print'] = REAL_PRINT

        # If there's been any output so far, print it out before the
        # error traceback is printed so we have context for debugging.
        output_so_far = output.getvalue()
        if output_so_far:
            print(output_so_far, end='', file=sys.stderr)

        if raise_exceptions:
            raise WrappedException(output_so_far) from e

        format_list = traceback.format_exception(*sys.exc_info())

        # Only show tracebacks for code that was in the target source file.
        # This way calls to parse(), compile(), and exec() are removed.
        cutoff = 0
        for cutoff, line in enumerate(format_list):
            if path in line:
                break

        formatted = ''.join(format_list[cutoff:])
        print('Traceback (most recent call last):', file=sys.stderr)
        print(formatted, end='', file=sys.stderr)
        raise MarkdownExecError(e)
    finally:
        # Restore the print function for other code in this module.
        context['print'] = REAL_PRINT
        # Disable the logging handler.
        logging.getLogger().removeHandler(logging_handler)

    return output.getvalue()


def exec_python2(source):
    source_bytes = source.encode('utf-8')
    output = subprocess.check_output(['python2.7'], input=source_bytes)
    return output.decode('utf-8')


def exec_syntax_error(source):
    source_bytes = source.encode('utf-8')
    child = subprocess.Popen(
        ['python3'],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE)
    _, output = child.communicate(input=source_bytes)
    output = output.decode('utf-8')
    # Only return the last line. The preceeding lines will be parts of
    # the stack trace that caused the syntax error.
    return output.strip('\n').split('\n')[-1]


filename_re = re.compile('[\\.]{0,2}/[-a-zA-Z0-9_/]+(\\.py|\\.md)')


def exec_exception(path, source, context):
    try:
        exec_source(path, source, context,
                    raise_exceptions=True)
    except WrappedException as e:
        original = e.__context__
        pretty_exception = str(original)
        pretty_exception = filename_re.sub('my_code.py', pretty_exception)
        exception_line = '%s: %s' % (
            original.__class__.__name__, pretty_exception)

        if e.output:
            return '%sTraceback ...\n%s' % (
                e.output, exception_line)
        else:
            return exception_line
    else:
        assert False, 'Exception not raised'


def iterate_blocks(path, text):
    text_start = 0
    source_start = None
    block_suffix = ''
    pending_source = ''
    pending_output = ''

    # Import the __main__ module, which is this file, and run all of the
    # Markdown code as if it's part of that module. This enables modules
    # like pickle to work, which need to use import paths relative to named
    # modules in order to serialized/deserialize functions.
    import __main__
    context = __main__.__dict__

    for blocks_seen, match in enumerate(re.finditer('```', text)):
        start = match.start()
        end = match.end()

        if blocks_seen % 2 == 0:
            # Figure out the language of the opening block.
            suffix_end = text.find('\n', end)
            if suffix_end > 0:
                block_suffix = text[end:suffix_end].lower()
                source_start = end + len(block_suffix)

            # All text until the block start
            yield text[text_start:start]
        else:
            text_start = end
            source = text[source_start:start]

            # Closing block
            if block_suffix in ('python', 'python-exception'):
                # Run any pending source immediately if this is a Python
                # exception block to ensure we re-raise unexpected exceptions
                # back up instead of just printing them into output blocks.
                if block_suffix == 'python-exception':
                    if pending_source:
                        pending_output += exec_source(
                            path, pending_source, context)
                        pending_source = ''

                # Add a bunch of blank lines before the source to get the line
                # numbers to match up during ast.parse. The ast.increment_lineno
                # helper is useful, but only after parsing was successful. If
                # you want helpful error messages during parsing you need to
                # fake it.
                line_offset = text[:source_start].count('\n')
                delta_offset = line_offset - pending_source.count('\n')
                pending_source += '\n' * delta_offset

                # Accumulate all the source code to run until we reach the
                # first output block *or* the end of the file.
                pending_source += source

                yield '```%s' % block_suffix
                yield source
                yield '```'

                if block_suffix == 'python-exception':
                    pending_output += exec_exception(
                        path, pending_source, context)
                    pending_source = ''
            elif block_suffix == 'python2':
                yield '```python2'
                if not source.startswith('\n# Python 2'):
                    yield '\n# Python 2'
                yield source
                yield '```'

                pending_output += exec_python2(source)
            elif block_suffix == 'python-syntax-error':
                yield '```python-syntax-error'
                yield source
                yield '```'

                pending_output += exec_syntax_error(source)
            elif block_suffix.startswith('python-include:'):
                include_path = block_suffix[len('python-include:'):]
                file_basename = os.path.basename(include_path)
                full_path = os.path.join(FLAGS.root_dir, include_path)
                data = open(full_path, 'r').read()

                yield '```%s\n' % block_suffix
                yield '# %s\n' % file_basename
                yield data.strip()
                yield '\n```'
            else:
                if pending_source:
                    pending_output += exec_source(
                        path, pending_source, context)
                    pending_source = ''
                elif not pending_output:
                    # This handles random output blocks in the Markdown file
                    # that do not follow Python blocks. This is helpful when
                    # you're sketching out a rough draft. Just pass through
                    # whatever the field was before.
                    pending_output = source

                # Output block
                yield '```%s\n' % block_suffix
                yield pending_output.strip('\n')
                yield '\n```'

                pending_output = ''

    # What follows the very last block to the end of the file
    yield text[text_start:]

    # Run any remaining pending code to make sure it doesn't have errors.
    if pending_source:
        exec_source(path, pending_source, context)


def print_iter(it, path, overwrite):
    output = sys.stdout
    if overwrite:
        output = io.StringIO()
    try:
        for text in it:
            print(text, end='', file=output)
    except:
        raise
    else:
        if overwrite:
            open(path, 'w', encoding='utf-8').write(output.getvalue())


def main():
    FLAGS.parse()

    for path in FLAGS.path:
        # Always use the same seed so multiple runs of the same Markdown files
        # will always produce the same output results.
        random.seed(1234)

        # Always pretend that we're running in Pacific Time
        os.environ['TZ'] = 'US/Pacific'
        tzset()

        # Kill the process if it's been running for longer than the timeout.
        signal.alarm(FLAGS.timeout_seconds)

        text = open(path, encoding='utf-8').read()
        it = iterate_blocks(path, text)
        try:
            print_iter(it, path, FLAGS.overwrite)
        except MarkdownExecError:
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
