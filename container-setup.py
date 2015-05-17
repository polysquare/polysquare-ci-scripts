# /container-setup.py
#
# Initial setup script specific to polysquare-ci-scripts. Downloads all
# language runtimes to be used in tests at the start and then passes control
# to general python project script.
#
# See /LICENCE.md for Copyright information
"""Initial setup script specific to polysquare-ci-scripts."""

from collections import defaultdict


def run(cont, util, shell, argv=None):
    """Set up language runtimes and pass control to python project script."""
    with util.Task("""Installing all necessary language runtimes"""):
        hs_ver = defaultdict(lambda: "7.8.4")
        configure_haskell = "setup/project/configure_haskell.py"
        configure_os = "setup/project/configure_os.py"

        cont.fetch_and_import(configure_haskell).run(cont, util, shell, hs_ver)
        cont.fetch_and_import(configure_os).run(cont, util, shell, None)

    cont.fetch_and_import("setup/python/setup.py").run(cont, util, shell, argv)

    with util.Task("""Preparing for this container to be copied later"""):
        cont.clean(util)

