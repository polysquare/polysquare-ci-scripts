# /ciscripts/setup/python/setup.py
#
# The main setup script to bootstrap and set up a python project.
#
# See /LICENCE.md for Copyright information
"""The main setup script to bootstrap and set up a python project."""


def run(cont, util, shell, argv=list()):
    """Install everything necessary to test and check a python project.

    This script installs language runtimes to the extent that they're necessary
    for the linter checks, however those runtimes won't be active at the
    time that tests are run.
    """
    del argv

    cont.fetch_and_import("setup/project/setup.py").run(cont, util, shell)

    with util.Task("Setting up python project"):
        py_ver = "2.7"
        hs_ver = "7.8.4"
        py_config_script = "setup/project/configure_python.py"
        hs_config_script = "setup/project/configure_haskell.py"
        py_util = cont.fetch_and_import("python_util.py")
        py_cont = cont.fetch_and_import(py_config_script).run(cont,
                                                              util,
                                                              shell,
                                                              py_ver)

        hs_container = cont.fetch_and_import(hs_config_script).run(cont,
                                                                   util,
                                                                   shell,
                                                                   hs_ver)

        with util.Task("Installing pandoc"):
            util.where_unavailable("pandoc",
                                   hs_container.install_cabal_pkg,
                                   cont,
                                   "pandoc")

        with util.Task("Installing python linters"):
            py_util.pip_install_deps(cont,
                                     util,
                                     "lint",
                                     "--process-dependency-links",
                                     "--allow-external",
                                     "pychecker",
                                     "--allow-unverified",
                                     "pychecker")

        with util.Task("Installing python test runners"):
            with py_cont.deactivated(util):
                py_util.pip_install_deps(cont,
                                         util,
                                         "test",
                                         "--process-dependency-links",
                                         "--allow-external",
                                         "nose-parameterized",
                                         "--allow-unverified",
                                         "nose-parameterized")
                py_util.pip_install(cont, util, "coverage", "coveralls")
