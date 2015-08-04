# /ciscripts/coverage/python/coverage.py
#
# Submit coverage total for a python project to coveralls
#
# See /LICENCE.md for Copyright information
"""The main setup script to bootstrap and set up a python project."""

import os

from collections import defaultdict


def run(cont, util, shell, argv=None):
    """Submit coverage total to coveralls."""
    del argv

    with util.Task("""Submitting coverage totals"""):
        py_ver = defaultdict(lambda: "3.4.1")
        configure_python = "setup/project/configure_python.py"
        py_cont = cont.fetch_and_import(configure_python).get(cont,
                                                              util,
                                                              shell,
                                                              py_ver)

        if os.environ.get("CI", None) is not None:
            with util.Task("""Uploading to coveralls"""):
                with py_cont.activated(util):
                    util.execute(cont, util.running_output, "coveralls",)
