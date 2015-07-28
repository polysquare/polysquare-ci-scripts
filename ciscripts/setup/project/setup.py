# /ciscripts/setup/project/setup.py
#
# The main setup script to bootstrap and set up a generic project.
#
# See /LICENCE.md for Copyright information
"""The main setup script to bootstrap and set up a generic project."""

import argparse

from collections import defaultdict


def run(cont, util, shell, argv=None):
    """Install everything necessary to test a generic project.

    This script installs ruby 2.1 and python 2.7 as well as
    markdownlint and polysquare-generic-file-linter. It provides actions
    to check every file in a directory for the polysquare style guide.
    """
    with util.Task("""Setting up generic project"""):
        parser = argparse.ArgumentParser(description="""Set up project""")
        parser.add_argument("--no-mdl",
                            help="""Do not install markdownlint""",
                            action="store_true")
        parse_result, _ = parser.parse_known_args(argv or list())

        config_python = "setup/project/configure_python.py"
        py_ver = defaultdict(lambda: "3.4.1")

        py_util = cont.fetch_and_import("python_util.py")
        cont.fetch_and_import(config_python).run(cont,
                                                 util,
                                                 shell,
                                                 py_ver)

        if not parse_result.no_mdl:
            config_ruby = "setup/project/configure_ruby.py"
            rb_ver = defaultdict(lambda: "2.1.5",
                                 Windows="2.1.6")

            rb_cont = cont.fetch_and_import(config_ruby).run(cont,
                                                             util,
                                                             shell,
                                                             rb_ver)

            with util.Task("""Installing markdownlint"""):
                util.where_unavailable("mdl",
                                       util.execute,
                                       cont,
                                       util.long_running_suppressed_output(),
                                       "gem",
                                       "install",
                                       "--conservative",
                                       "--no-ri",
                                       "--no-rdoc",
                                       "mdl",
                                       instant_fail=True,
                                       path=rb_cont.executable_path())

        with util.Task("""Installing polysquare style guide linter"""):
            py_util.pip_install(cont,
                                util,
                                "polysquare-generic-file-linter>=0.1.1",
                                instant_fail=True)
