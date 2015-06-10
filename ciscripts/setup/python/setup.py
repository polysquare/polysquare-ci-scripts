# /ciscripts/setup/python/setup.py
#
# The main setup script to bootstrap and set up a python project.
#
# See /LICENCE.md for Copyright information
"""The main setup script to bootstrap and set up a python project."""

import platform

from collections import defaultdict


def _install_test_dependencies(cont, util, py_util):
    """Install testing dependencies for python project."""
    py_util.pip_install_deps(cont,
                             util,
                             "green",
                             "--process-dependency-links",
                             "--allow-external",
                             "nose-parameterized",
                             "--allow-unverified",
                             "nose-parameterized")


def _prepare_python_deployment(cont, py_cont, util, shell, py_util):
    """Install dependencies required to deploy python project."""
    hs_ver = defaultdict(lambda: "7.8.4")
    hs_config_script = "setup/project/configure_haskell.py"
    hs_container = cont.fetch_and_import(hs_config_script).run(cont,
                                                               util,
                                                               shell,
                                                               hs_ver)

    with util.Task("""Installing pandoc"""):
        util.where_unavailable("pandoc",
                               hs_container.install_cabal_pkg,
                               cont,
                               "pandoc")

    with util.Task("""Installing deploy dependencies"""):
        with py_cont.deactivated(util):
            py_util.pip_install_deps(cont, util, "upload")


def _upgrade_pip(cont, util):
    """Upgrade pip installation in current virtual environment."""
    util.execute(cont,
                 util.long_running_suppressed_output(),
                 "pip",
                 "install",
                 "--upgrade",
                 "pip")


def run(cont, util, shell, argv=None):
    """Install everything necessary to test and check a python project.

    This script installs language runtimes to the extent that they're necessary
    for the linter checks, however those runtimes won't be active at the
    time that tests are run.
    """
    cont.fetch_and_import("setup/project/setup.py").run(cont,
                                                        util,
                                                        shell,
                                                        argv)

    with util.Task("""Setting up python project"""):
        py_ver = defaultdict(lambda: "2.7.9")
        py_config_script = "setup/project/configure_python.py"
        py_util = cont.fetch_and_import("python_util.py")
        py_cont = cont.fetch_and_import(py_config_script).run(cont,
                                                              util,
                                                              shell,
                                                              py_ver)

        # Upgrading pip on Windows fails with permission
        # errors when attempting to remove the old version of
        # pip, so don't perform, the upgrade on Windows
        if platform.system() != "Windows":
            with util.Task("""Upgrading pip"""):
                with py_cont.deactivated(util):
                    _upgrade_pip(cont, util)

                _upgrade_pip(cont, util)

        with util.Task("""Installing python linters"""):
            py_util.pip_install_deps(cont,
                                     util,
                                     "polysquarelint",
                                     "--process-dependency-links",
                                     "--allow-external",
                                     "pychecker",
                                     "--allow-unverified",
                                     "pychecker")

        with util.Task("""Installing python test runners"""):
            # Install testing dependencies both inside and outside container.
            # They need to be installed in the container so that static
            # analysis tools can successfully import them.
            with py_cont.deactivated(util):
                _install_test_dependencies(cont, util, py_util)
                py_util.pip_install(cont, util, "coverage")

            _install_test_dependencies(cont, util, py_util)
            py_util.pip_install(cont, util, "coverage", "coveralls")

        util.prepare_deployment(_prepare_python_deployment,
                                cont,
                                py_cont,
                                util,
                                shell,
                                py_util)
