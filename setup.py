#!/usr/bin/env python3

from setuptools import setup

setup(
    name = 'pyliterate',
    packages = ['pyliterate'],
    version = '0.1',
    description = 'Literate programming with Python',
    author = 'Brett Slatkin',
    author_email = 'brett@haxor.com',
    url = 'https://github.com/bslatkin/pyliterate',
    keywords = [],
    entry_points={
        'console_scripts': [
            'run_markdown=pyliterate.run_markdown:main',
        ]
    },
    classifiers = [
    ],
    long_description = """\
"""
)
