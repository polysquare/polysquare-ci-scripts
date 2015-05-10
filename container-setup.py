# /container-setup.py
#
# Initial setup script specific to polysquare-ci-scripts. Downloads all
# language runtimes to be used in tests at the start and then passes control
# to general python project script.
#
# See /LICENCE.md for Copyright information
"""Initial setup script specific to polysquare-ci-scripts."""

from collections import defaultdict


def run(cont, util, shell, argv=list()):
    """Set up language runtimes and pass control to python project script."""

    with util.Task("""Installing all necessary language runtimes"""):
        rb_ver = defaultdict(lambda: "2.1.5", Windows="2.1.6")
        py_ver = defaultdict(lambda: "2.7.9")
        hs_ver = defaultdict(lambda: "7.8.4")

        configure_ruby = "setup/project/configure_ruby.py"
        configure_python = "setup/project/configure_python.py"
        configure_haskell = "setup/project/configure_haskell.py"

        cont.fetch_and_import(configure_ruby).run(cont, util, shell, rb_ver)
        cont.fetch_and_import(configure_python).run(cont, util, shell, py_ver)
        cont.fetch_and_import(configure_haskell).run(cont, util, shell, hs_ver)

    cont.fetch_and_import("setup/python/setup.py").run(cont, util, shell, argv)
