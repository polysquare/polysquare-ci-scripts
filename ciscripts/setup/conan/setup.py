# /ciscripts/setup/conan/setup.py
#
# The main setup script to bootstrap and set up a conan project.
#
# See /LICENCE.md for Copyright information
"""The main setup script to bootstrap and set up a conan project."""

from collections import defaultdict


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

    config_python = "setup/project/configure_python.py"
    py_ver = util.language_version("python3")
    py_util = cont.fetch_and_import("python_util.py")
    py_cont = cont.fetch_and_import(config_python).run(cont,
                                                       util,
                                                       shell,
                                                       py_ver)

    with util.Task("""Setting up conan project"""):
        with py_cont.activated(util):
            py_util.pip_install(cont,
                                util,
                                "http://github.com/smspillaz/conan/archive/"
                                "additional-py3-setup-fixes.tar.gz"
                                "#egg=conan-0.9.0")

    meta_container = util.make_meta_container([py_cont, os_cont],
                                              execute=util.execute)

    util.register_result("_POLYSQUARE_SETUP_CONAN_PROJECT", meta_container)
    return meta_container
