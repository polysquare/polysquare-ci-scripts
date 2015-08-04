# /ciscripts/setup/bii/setup.py
#
# The main setup script to bootstrap and set up a bii project.
#
# See /LICENCE.md for Copyright information
"""The main setup script to bootstrap and set up a bii project."""

import os

from collections import defaultdict


def _get_bii_container(cont, util, shell, argv, os_cont):
    """Get bii container to run this project in."""
    return cont.fetch_and_import("setup/project/configure_bii.py").run(cont,
                                                                       util,
                                                                       shell,
                                                                       argv,
                                                                       os_cont)


def run(cont, util, shell, argv=None):
    """Install everything necessary to test and check a bii project.

    This script installs language runtimes to the extent that they're necessary
    for the linter checks, however those runtimes won't be active at the
    time that tests are run.
    """
    result = util.already_completed("_POLYSQUARE_SETUP_BII_PROJECT")
    if result is not util.NOT_YET_COMPLETED:
        return result

    cont.fetch_and_import("setup/project/setup.py").run(cont,
                                                        util,
                                                        shell,
                                                        argv)
    configure_ruby = "setup/project/configure_ruby.py"
    ruby_version = defaultdict(lambda: "2.1.5")
    rb_cont = cont.fetch_and_import(configure_ruby).get(cont,
                                                        util,
                                                        shell,
                                                        ruby_version)

    if not os.environ.get("APPVEYOR", None):
        rb_util = cont.fetch_and_import("ruby_util.py")
        with rb_cont.activated(util):
            util.where_unavailable("coveralls-lcov",
                                   rb_util.gem_install,
                                   cont,
                                   util,
                                   "coveralls-lcov",
                                   instant_fail=True,
                                   path=rb_cont.executable_path())

    extra_packages = defaultdict(lambda: defaultdict(lambda: []),
                                 Linux=defaultdict(lambda: [
                                     "python",
                                     "python-pip",
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

    with util.Task("""Setting up bii project"""):
        bii_meta = _get_bii_container(cont, util, shell, argv, os_cont)

    util.register_result("_POLYSQUARE_SETUP_BII_PROJECT", bii_meta)
    return bii_meta
