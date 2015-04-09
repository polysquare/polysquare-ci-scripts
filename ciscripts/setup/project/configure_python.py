# /ciscripts/setup/project/configure_python.py
#
# A script which configures and activates a python installation
#
# See /LICENCE.md for Copyright information
"""A script which configures and activates a python installation."""

import fnmatch

import os
import os.path

import shutil


def get(container, util, shell, version):
    """Return a PythonContainer for an installed python in container."""
    container_path = os.path.join(container.language_dir("python"),
                                  version)

    class PythonContainer(container.new_container_for("python", version)):

        """A container representing an active python installation."""

        def __init__(self, version, installation, shell):
            """Initialize a python container for this version."""
            super(PythonContainer, self).__init__(installation,
                                                  "python",
                                                  version,
                                                  shell)

            self._version = version
            assert os.path.exists(self._installation)

        @staticmethod
        def _get_py_path_from(installation):
            """Given an installation, get the python library dir."""
            py_lib = os.path.join(installation, "lib")
            py_path = fnmatch.filter(os.listdir(py_lib), "python*")

            assert len(py_path) == 1
            return py_path[0]

        def clean(self, util):  # suppress(unused-function)
            """Clean out cruft in the container."""
            py_path = PythonContainer._get_py_path_from(self._installation)

            util.apply_to_files(os.unlink, py_path, matching=["*.pyc"])
            util.apply_to_files(os.unlink, py_path, matching=["*.pyo"])

            util.apply_to_directories(shutil.rmtree,
                                      py_path,
                                      matching=["*/test/*"])

        def _active_environment(self, tuple_type):
            """Return active environment for python container."""
            py_path = PythonContainer._get_py_path_from(self._installation)
            env_to_overwrite = {
                "PYTHONDONTWRITEBYTECODE": 1,
                "PYTHONPATH": os.path.join(py_path, "site-packages"),
                "VIRTUAL_ENV": self._installation
            }
            env_to_append = {
                "PATH": os.path.join(self._installation,
                                     "bin")
            }

            return tuple_type(overwrite=env_to_overwrite, append=env_to_append)

    return PythonContainer(version, container_path, shell)


def run(container, util, shell, version):
    """Install and activates a python installation.

    This function returns a PythonContainer, which has a path
    and keeps a reference to its parent container.
    """
    class PythonBuildManager(object):

        """An object wrapping the python-build script."""

        def __init__(self, container):
            """Initialize the python-build script."""
            super(PythonBuildManager, self).__init__()
            lang_dir = container.language_dir("python")
            self._python_build_dir = os.path.join(lang_dir, "build")

            if not os.path.exists(self._python_build_dir):
                with container.in_temp_cache_dir() as tmp:
                    with util.Task("Downloading pyenv"):
                        remote = "git://github.com/yyuu/pyenv"
                        util.execute(container,
                                     util.output_on_fail,
                                     "git", "clone", remote, tmp,
                                     instant_fail=True)
                    with util.Task("Installing pyenv"):
                        util.execute(container,
                                     util.output_on_fail,
                                     "bash",
                                     os.path.join(tmp,
                                                  "plugins",
                                                  "python-build",
                                                  "install.sh"),
                                     env={
                                         "PREFIX": self._python_build_dir
                                     },
                                     instant_fail=True)

        def install(self, version):
            """Install python version, returning a PythonContainer."""
            py_cont = os.path.join(container.language_dir("python"),
                                   version)
            download_cache = container.named_cache_dir("python-download")
            build_cache = container.named_cache_dir("python-build")

            if not os.path.exists(py_cont):
                with util.Task("Installing python version " + version):
                    py_build = os.path.join(self._python_build_dir,
                                            "bin",
                                            "python-build")
                    util.execute(container,
                                 util.long_running_suppressed_output(),
                                 "bash",
                                 py_build,
                                 "--skip-existing",
                                 version,
                                 py_cont,
                                 env={
                                     "PYTHON_BUILD_CACHE_PATH": download_cache,
                                     "PYTHON_BUILD_BUILD_PATH": build_cache
                                 },
                                 instant_fail=True)

            return get(container, util, shell, version)

    with util.Task("Configuring python"):
        python_container = PythonBuildManager(container).install(version)
        with util.Task("Activating python {0}".format(version)):
            python_container.activate(util)

        return python_container
