# /ciscripts/parse_setup.py
#
# Python utility script to read a /setup.py file and dump requested fields.
#
# It should be used like so:
#   python /parse_setup.py FIELD [FIELD...]
#
# See /LICENCE.md for Copyright information
"""Python related utility functions."""

import json

import sys

import warnings

from contextlib import contextmanager


def main(argv):
    """Parse /setup.py and return requested fields."""
    setuptools_arguments = dict()

    @contextmanager
    def patched_setuptools():
        """Import setuptools and patch it."""
        import setuptools

        def setup_hook(*args, **kwargs):
            """Override the setup function and log its arguments."""
            del args

            setuptools_arguments.update(kwargs)

        old_setup = setuptools.setup
        setuptools.setup = setup_hook

        try:
            yield
        finally:
            setuptools.setup = old_setup

    with patched_setuptools():
        import imp
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            imp.load_source("setup.py", "setup.py")

    return {k: setuptools_arguments[k] for k in argv
            if k in setuptools_arguments}

sys.stdout.write(json.dumps(main(sys.argv[1:])))
