# PyLiterate

This is the tool I used to write my book, [Effective Python](http://www.effectivepython.com). The workflow is a variation on [Donald Knuth's Literate programming](http://en.wikipedia.org/wiki/Literate_programming).

The idea is the source code and explanatory text appear interleaved in a [Markdown formatted](https://help.github.com/articles/github-flavored-markdown/) file. Each time you edit a Markdown file, you can re-run the source code it contains using the `run_markdown` tool provided by this project (it's super userful as a Sublime build system). `run_markdown` will update the file in-place with the new output from running the code. If an unexpected error occurs it will be printed to the terminal instead of overwriting the file.

The example book source contained in this project has multiple chapters (directories) containing multiple subsections (files). By having these subsections in separate files, it becomes a lot easier to focus on each individual subject as you write. The example `Makefile` also shows how all of the pieces can be connected together.

In the case of my book, the final step was post-processing the Markdown file and converting it into a Microsoft Word document. This was a requirement of my publisher because of the way their book printing workflow was built. You can [learn more about how I wrote my book here](http://www.onebigfluke.com/2014/07/how-im-writing-programming-book.html).

## Example usage

See the `example` directory for the layout of a simple book. This includes an example `Makefile` that ties it all together. To run the example, run the following commands from a clean check-out of this project. Make sure you have Python 3 installed.

Create a virtual environment:

`pyvenv .`

Activate the virtual environment:

`source bin/activate`

Install this package in your virtual environment:

`pip install -e .`

Go into the example directory:

`cd example`

Run all of the Markdown files and have them overwritten in place:

`make run`

Build the whole book output:

`make output/Book_draft.md`

Making the book will also output diffs of each section after the source is re-run. This allows you to see if running the latest version of the code in the Markdown files changes the output in any way.

When you're done with everything, you can delete the output files:

`make clean`

And finally, deactivate your virtual environment:

`deactivate`

## Markdown format

The `run_markdown` tool looks for code blocks like this in Markdown files (that end with the `.md` suffix):

    ```python
    print('Hello world')
    ```

The tool will run the code top-to-bottom in the file. When a non-Python block like this is found (it also can be empty):

    ```
    Output goes here
    ```

All of the prior Python blocks are combined together, run, and their combined output is inserted (`Hello world` in this case). Not every Python block needs to have an output block, but every output block needs at least one preceeding Python block to produce output.

Python blocks do not have to be stand-alone code blocks. A single class or function definition can be interleaved with text. For example, this is legal:

    ```python
    def multiply(a, b):
    ```

    And the body is:

    ```python
        return a * b
    ```

Here's a list of various detailed features that are provided by the `run_markdown` tool:

- `pprint` function is always available without import
- `debug` function will write output to stderr but not insert it into the Markdown file's output
- `Pdb.set_trace()` will actually stop execution in the Markdown file so you can debug as the program runs
- Exception tracebacks and PDB step line numbers are all given as line numbers in the original Markdown file
- Use ```````python```` to run a code snippet as Python 3 source. This will automatically inherit all of the state of the program for any snippets that are higher up in the Markdown file
- Use ```````python2```` to run a code snippet as Python 2 source instead of Python 3. Notably, Python 2 snippets will not inherit the Python execution state from higher up in the file, they are limited to the containing ``` block
- Use ```````python-exception```` for expected exceptions for which you want to insert the exception name and error message back into the Markdown file
- Use ```````python-syntax-error```` for examples that contain syntax errors that you want to insert back into the Markdown file
- Use ```````python-include:path/to/file.py```` to include an external Python file relative to the `--root_dir` flag, which defaults to the root of the book directory. This will automatically insert a comment of the source file's relative path at the top of the included source
- The `random.seed` is always set to `1234` so your random functions have predictable output
- The timezone is always set to `US/Pacific` so your code runs in the same timezone regardless of where your computer currently is located
- The script will only be allowed to run for `--timeout_seconds` before being terminated (defaults to 5 seconds)

## TODO

- Clean up the Python style
- Write better docstrings
- Write some tests (for things like `debug`, `pprint`, and `Pdb`)
- Actually upload this to PyPI
- Add a Travis build for example data
