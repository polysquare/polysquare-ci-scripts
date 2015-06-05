# /ciscripts/setup/project/configure_python.py
#
# A script which configures and activates a python installation
#
# See /LICENCE.md for Copyright information
"""A script which configures and activates a python installation."""

import errno

import fnmatch

import os
import os.path

import platform

import shutil

from collections import defaultdict

from contextlib import closing


def get(container, util, shell, ver_info):
    """Return a PythonContainer for an installed python in container."""
    del util

    version = ver_info[platform.system()]
    if os.environ.get("POLYSQUARE_PREINSTALLED_PYTHON", None):
        container_path = os.environ["POLYSQUARE_PREINSTALLED_PYTHON"]
    else:
        container_path = os.path.join(container.language_dir("python"),
                                      version)

    # This class is intended to be used through LanguageBase, so
    # most of its methods are private
    #
    # suppress(too-few-public-methods)
    class PythonContainer(container.new_container_for("python", version)):

        """A container representing an active python installation."""

        # pylint can't detect that this is a new-style class
        #
        # suppress(super-on-old-class)
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
            if platform.system() in ("Linux", "Darwin"):
                lib_subdirectory = "lib"
                py_lib = os.path.join(installation, lib_subdirectory)
                py_path = fnmatch.filter(os.listdir(py_lib), "python*")

                assert len(py_path) == 1
                return os.path.join(py_lib, py_path[0])
            elif platform.system() in ("Windows", ):
                lib_subdirectory = "Lib"
                return os.path.join(installation, lib_subdirectory)

            return None

        @staticmethod
        def _get_exec_path_from(installation):
            """Given an installation, get python binary path.

            This may have more than one component, depending on
            the platform specified.
            """
            if platform.system() in ("Linux", "Darwin"):
                comp = ["bin"]
                sep = ":"
            elif platform.system() in ("Windows", ):
                comp = ["", os.path.join("Scripts")]
                sep = ";"

            return sep.join([os.path.normpath(os.path.join(installation,
                                                           c)) for c in comp])

        # suppress(super-on-old-class)
        def clean(self, util_mod):
            """Clean out cruft in the container."""
            super(PythonContainer, self).clean(util_mod)

            py_path = self._installation

            util_mod.apply_to_files(os.unlink, py_path, matching=["*.a"])

            util_mod.apply_to_files(os.unlink, py_path, matching=["*.pyc"])
            util_mod.apply_to_files(os.unlink, py_path, matching=["*.pyo"])
            util_mod.apply_to_files(os.unlink, py_path, matching=["*.chm"])
            util_mod.apply_to_files(os.unlink, py_path, matching=["*.html"])
            util_mod.apply_to_files(os.unlink, py_path, matching=["*.pyo"])
            util_mod.apply_to_files(os.unlink, py_path, matching=["*.whl"])
            util_mod.apply_to_files(os.unlink,
                                    py_path,
                                    matching=["*.egg-link"])

            util_mod.apply_to_directories(shutil.rmtree,
                                          py_path,
                                          matching=["*/test/*"])
            util_mod.apply_to_directories(shutil.rmtree,
                                          py_path,
                                          matching=["*/tcl/*"])

            def reset_mtime(path):
                """Reset modification time of file at path to 1.

                This is needed for files that change on every installation,
                such that they don't cause caches to be spuriously
                invalidated.
                """
                os.utime(path, (1, 1))

            pkg_path = os.path.join(PythonContainer._get_py_path_from(py_path),
                                    "site-packages")

            reset_mtime(os.path.join(pkg_path, "easy-install.pth"))
            util_mod.apply_to_files(reset_mtime,
                                    pkg_path,
                                    matching=["*.pth"])
            util_mod.apply_to_files(reset_mtime,
                                    os.path.join(py_path, "bin"),
                                    matching=["*"])
            util_mod.apply_to_files(reset_mtime,
                                    os.path.join(py_path, "Scripts"),
                                    matching=["*"])

        def _active_environment(self, tuple_type):
            """Return active environment for python container."""
            py_path = PythonContainer._get_py_path_from(self._installation)
            exec_path = PythonContainer._get_exec_path_from(self._installation)
            env_to_overwrite = {
                "PYTHONDONTWRITEBYTECODE": 1,
                "PYTHONPATH": os.path.join(py_path, "site-packages"),
                "VIRTUAL_ENV": self._installation
            }
            env_to_prepend = {
                "PATH": exec_path
            }

            return tuple_type(overwrite=env_to_overwrite,
                              prepend=env_to_prepend)

    return PythonContainer(version, container_path, shell)


def posix_installer(lang_dir, python_build_dir, util, container, shell):
    """Use pyenv to install python on a posix-compatible operating system."""
    if not os.path.exists(python_build_dir):
        with container.in_temp_cache_dir() as tmp:
            with util.Task("""Downloading pyenv"""):
                remote = "git://github.com/yyuu/pyenv"
                util.execute(container,
                             util.output_on_fail,
                             "git", "clone", remote, tmp,
                             instant_fail=True)
            with util.Task("""Installing pyenv"""):
                util.execute(container,
                             util.output_on_fail,
                             "bash",
                             os.path.join(tmp,
                                          "plugins",
                                          "python-build",
                                          "install.sh"),
                             env={
                                 "PREFIX": python_build_dir
                             },
                             instant_fail=True)

    def install(version):
        """Install python version, returning a PythonContainer."""
        py_cont = os.path.join(lang_dir, version)
        download_cache = container.named_cache_dir("python-download")
        build_cache = container.named_cache_dir("python-build")

        if not os.path.exists(py_cont):
            with util.Task("""Installing python version """ + version):
                py_build = os.path.join(python_build_dir,
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

        return get(container, util, shell, defaultdict(lambda: version))

    return install


def windows_installer(lang_dir, python_build_dir, util, container, shell):
    """Use officially provided installer to install python on Windows."""
    try:
        os.makedirs(python_build_dir)
    except OSError as error:
        if error.errno != errno.EEXIST:   # suppress(PYC90)
            raise error

    def install(version):
        python_version_container = os.path.join(lang_dir, version)

        if not os.path.exists(python_version_container):
            url = ("https://www.python.org/ftp/python/{ver}/"
                   "python-{ver}.msi").format(ver=version)
            with open(os.path.join(python_build_dir,
                                   version + "-install.exe"),
                      "wb") as installer:
                remote = util.url_opener()(url.format(ver=version))
                with closing(remote):
                    installer.write(remote.read())

            with util.Task("""Installing python version """ + version):
                installer = os.path.realpath(installer.name)
                util.execute(container,
                             util.long_running_suppressed_output(),
                             "msiexec",
                             "/i",
                             installer,
                             "/qn",
                             "TARGETDIR=" + python_version_container,
                             "ADDLOCAL=pip_feature")
                os.unlink(installer)

        return get(container, util, shell, defaultdict(lambda: version))

    return install


def pre_existing_python(lang_dir, python_build_dir, util, container, shell):
    """Use pre-installed python."""
    del python_build_dir
    del lang_dir

    def install(version):
        """Use system installation directory."""
        with util.Task("Using system installation"):
            return get(container, util, shell, defaultdict(lambda: version))

    return install


def run(container, util, shell, ver_info):
    """Install and activates a python installation.

    This function returns a PythonContainer, which has a path
    and keeps a reference to its parent container.
    """
    lang_dir = container.language_dir("python")
    python_build_dir = os.path.join(lang_dir, "build")

    if (os.environ.get("POLYSQUARE_PREINSTALLED_PYTHON", None) and
            os.path.exists(os.environ["POLYSQUARE_PREINSTALLED_PYTHON"])):
        installer = pre_existing_python
    elif platform.system() in ("Linux", "Darwin"):
        installer = posix_installer
    elif platform.system() == "Windows":
        installer = windows_installer

    with util.Task("""Configuring python"""):
        version = ver_info[platform.system()]
        python_container = installer(lang_dir,
                                     python_build_dir,
                                     util,
                                     container,
                                     shell)(version)
        with util.Task("""Activating python {0}""".format(version)):
            python_container.activate(util)

        return python_container
