# /ciscripts/setup/python/setup.py
#
# The main setup script to bootstrap and set up a python project.
#
# See /LICENCE.md for Copyright information
"""The main setup script to bootstrap and set up a python project."""


def _install_test_dependencies(cont, util, py_util, *args):
    """Install testing dependencies for python project."""
    py_util.pip_install_deps(cont,
                             util,
                             "green",
                             *args)
    py_util.pip_install(cont,
                        util,
                        "setuptools-green>=0.0.13")


def _prepare_python_deployment(cont, util, py_util):
    """Install dependencies required to deploy python project."""
    with util.Task("""Installing deploy dependencies"""):
        py_util.pip_install_deps(cont, util, "upload")
        py_util.pip_install(cont, util, "twine")


def run(cont, util, shell, argv=None):
    """Install everything necessary to test and check a python project.

    This script installs language runtimes to the extent that they're necessary
    for the linter checks, however those runtimes won't be active at the
    time that tests are run.
    """
    result = util.already_completed("_POLYSQUARE_SETUP_PYTHON")
    if result is not util.NOT_YET_COMPLETED:
        return result

    meta_cont = cont.fetch_and_import("setup/project/setup.py").run(cont,
                                                                    util,
                                                                    shell,
                                                                    argv)

    with util.Task("""Setting up python project"""):
        py_ver = util.language_version("python3")
        py_config_script = "setup/project/configure_python.py"
        py_util = cont.fetch_and_import("python_util.py")
        py_cont = cont.fetch_and_import(py_config_script).run(cont,
                                                              util,
                                                              shell,
                                                              py_ver)

        with util.Task("""Installing python linters"""):
            with py_cont.activated(util):
                py_util.pip_install_deps(cont,
                                         util,
                                         "polysquarelint")
                py_util.pip_install(cont,
                                    util,
                                    "polysquare-setuptools-lint>=0.0.38")

        with util.Task("""Installing python test runners"""):
            _install_test_dependencies(cont,
                                       util,
                                       py_util,
                                       "coverage")

            # Install testing dependencies both inside and outside container.
            # They need to be installed in the container so that static
            # analysis tools can successfully import them.
            with py_cont.activated(util):
                _install_test_dependencies(cont,
                                           util,
                                           py_util,
                                           "coverage",
                                           "coveralls")

        util.prepare_deployment(_prepare_python_deployment,
                                cont,
                                util,
                                py_util)

        util.register_result("_POLYSQUARE_SETUP_PYTHON", meta_cont)
        return meta_cont
