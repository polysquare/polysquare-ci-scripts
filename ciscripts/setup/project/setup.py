# /ciscripts/setup/project/setup.py
#
# The main setup script to bootstrap and set up a generic project.
#
# See /LICENCE.md for Copyright information
"""The main setup script to bootstrap and set up a generic project."""


def run(cont, util, shell, argv=None):
    """Install everything necessary to test a generic project.

    This script installs ruby 1.9.3 and python 2.7 as well as
    markdownlint and polysquare-generic-file-linter. It provides actions
    to check every file in a directory for the polysquare style guide.
    """
    del argv

    with util.Task("Setting up generic project"):
        rb_ver = "2.1.5"
        py_ver = "2.7"

        py_util = cont.fetch_and_import("python_util.py")
        config_python = "setup/project/configure_python.py"
        config_ruby = "setup/project/configure_ruby.py"

        cont.fetch_and_import(config_ruby).run(cont,
                                               util,
                                               shell,
                                               rb_ver)
        py_cont = cont.fetch_and_import(config_python).run(cont,
                                                           util,
                                                           shell,
                                                           py_ver)

        with util.Task("Installing markdownlint"):
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
                                   instant_fail=True)

        with util.Task("Installing polysquare style guide linter"):
            linter = "polysquare-generic-file-linter"
            util.where_unavailable(linter,
                                   py_util.pip_install,
                                   py_cont,
                                   util,
                                   linter)
