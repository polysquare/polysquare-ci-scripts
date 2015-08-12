# /container-setup.py
#
# Initial setup script specific to polysquare-ci-scripts. Downloads all
# language runtimes to be used in tests at the start and then passes control
# to general python project script.
#
# See /LICENCE.md for Copyright information
"""Initial setup script specific to polysquare-ci-scripts."""


def run(cont, util, shell, argv=None):
    """Set up language runtimes and pass control to python project script."""
    with util.Task("""Installing all necessary language runtimes"""):
        hs_ver = util.language_version("haskell")
        configure_haskell = "setup/project/configure_haskell.py"

        cont.fetch_and_import(configure_haskell).run(cont, util, shell, hs_ver)

    cont.fetch_and_import("setup/bii/setup.py").run(cont, util, shell, argv)
    cont.fetch_and_import("setup/python/setup.py").run(cont, util, shell, argv)

    with util.Task("""Preparing for this container to be copied later"""):
        cont.clean(util)
