# /ciscripts/setup/conan/setup.py
#
# The main setup script to bootstrap and set up a conan project.
#
# See /LICENCE.md for Copyright information
"""The main setup script to bootstrap and set up a conan project."""

from collections import defaultdict


def _get_conan_container(cont, util, shell, argv, os_cont):
    """Get conan container to run this project in."""
    configure_conan = "setup/project/configure_conan.py"
    return cont.fetch_and_import(configure_conan).run(cont,
                                                      util,
                                                      shell,
                                                      argv,
                                                      os_cont=os_cont)


def run(cont, util, shell, argv=None):
    """Install everything necessary to test and check a conan project.

    This script installs language runtimes to the extent that they're necessary
    for the linter checks, however those runtimes won't be active at the
    time that tests are run.
    """
    result = util.already_completed("_POLYSQUARE_SETUP_CONAN_PROJECT")
    if result is not util.NOT_YET_COMPLETED:
        return result

    cont.fetch_and_import("setup/project/setup.py").run(cont,
                                                        util,
                                                        shell,
                                                        argv)

    extra_packages = defaultdict(lambda: defaultdict(lambda: []),
                                 Linux=defaultdict(lambda: [
                                     "ninja-build"
                                 ]),
                                 Windows=defaultdict(lambda: [
                                     "ninja"
                                 ]),
                                 Darwin=defaultdict(lambda: [
                                     "ninja"
                                 ]))

    extra_repos = defaultdict(lambda: defaultdict(lambda: []),
                              Linux=defaultdict(lambda: [
                                  "{ubuntu} {release} universe"
                              ]))

    os_cont = cont.fetch_and_import("setup/cmake/setup.py").run(cont,
                                                                util,
                                                                shell,
                                                                argv,
                                                                extra_packages,
                                                                extra_repos)

    with util.Task("""Setting up conan project"""):
        conan_meta = _get_conan_container(cont, util, shell, argv, os_cont)

    util.register_result("_POLYSQUARE_SETUP_CONAN_PROJECT", conan_meta)
    return conan_meta
