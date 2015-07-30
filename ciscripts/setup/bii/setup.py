# /ciscripts/setup/bii/setup.py
#
# The main setup script to bootstrap and set up a bii project.
#
# See /LICENCE.md for Copyright information
"""The main setup script to bootstrap and set up a bii project."""


def run(cont, util, shell, argv=None):
    """Install everything necessary to test and check a bii project.

    This script installs language runtimes to the extent that they're necessary
    for the linter checks, however those runtimes won't be active at the
    time that tests are run.
    """
    cont.fetch_and_import("setup/project/setup.py").run(cont,
                                                        util,
                                                        shell,
                                                        argv)

    with util.Task("""Setting up bii project"""):
        cont.fetch_and_import("setup/project/configure_bii.py").run(cont,
                                                                    util,
                                                                    shell,
                                                                    argv)

    return cont.fetch_and_import("setup/cmake/setup.py").run(cont,
                                                             util,
                                                             shell,
                                                             argv)
