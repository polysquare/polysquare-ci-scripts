# /ciscripts/python_util.py
#
# Python related utility functions.
#
# Note that in all these functions we are invoking python as a subprocess
# as opposed to using python directly. The user may have selected a different
# python version. This script happens to be written in python, but its just
# a script.
#
# See /LICENCE.md for Copyright information
"""Python related utility functions."""

import fnmatch

import hashlib

import json

import os

import re

import subprocess

from collections import defaultdict

from distutils.version import LooseVersion   # suppress(import-error)

from itertools import chain


_KNOWN_PYTHON_INSTALLATIONS = dict()


# suppress(invalid-name)
def _get_python_version_from_specified(version, precision):
    """Get python version at precision from specified python_executable."""
    return ".".join(version.split(" ")[1].split(".")[0:precision]).strip()


def _get_python_version_string(python_executable):
    """Get the version string for a python executable."""
    output = subprocess.Popen([python_executable, "--version"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).communicate()
    return "".join([o.decode() for o in output])


def get_python_version(util, precision):  # suppress(unused-function)
    """Get python version at precision.

    1 gets the major version, 2 gets major and minor, 3 gets the patch version.
    Use distutils' version comparison functions to compare between versions.

    Note that on some implementations of python the version output comes
    through on stdout, on others it comes through on stderr. Just join them
    both and parse the whole string.
    """
    version_string = _get_python_version_string(util.which("python"))
    return _get_python_version_from_specified(version_string, precision)


def discover_pythons():
    """Search PATH for python installations and return as dictionary.

    Each key is a python version and the value corresponds to the location
    of that python installation on disk.
    """
    if len(_KNOWN_PYTHON_INSTALLATIONS.keys()):
        return _KNOWN_PYTHON_INSTALLATIONS

    for path_component in os.environ.get("PATH", "").split(os.pathsep):
        try:
            dir_contents = os.listdir(path_component)
        except OSError:
            continue

        candidates = set()
        candidates |= set(fnmatch.filter(dir_contents, "python"))
        candidates |= set(fnmatch.filter(dir_contents, "python.exe"))
        candidates |= set(fnmatch.filter(dir_contents, "python[23]"))
        candidates |= set(fnmatch.filter(dir_contents,
                                         "python*[0123456789]"))
        candidates |= set(fnmatch.filter(dir_contents,
                                         "python*[0123456789]*[mud]"))

        # Make everything absolute again, remove symlinks
        candidates = set([os.path.join(path_component, c) for c in candidates])
        candidates = set([p for p in candidates if not os.path.islink(p)])

        candidate_versions = {
            python_executable: _get_python_version_string(python_executable)
            for python_executable in candidates
        }

        _KNOWN_PYTHON_INSTALLATIONS.update({
            _get_python_version_from_specified(version_string, 3): python_exec
            for python_exec, version_string in candidate_versions.items()
            if not python_is_pypy(version_string)
        })

        for version, python in _KNOWN_PYTHON_INSTALLATIONS.items():
            import sys
            sys.stderr.write("Found python {} {}\n".format(python, version))

    return _KNOWN_PYTHON_INSTALLATIONS


def fetch_packages_in_active_python():
    """Fetch a dict of installed packages for the current python.

    The dict shall have the format { "package": "version" }.
    """
    return dict([
        (x["name"], x["version"]) for x in
        json.loads(subprocess.check_output([
            "pip",
            "list",
            "--format=json",
            "--disable-pip-version-check"
        ]).decode())
    ])

_PACKAGES_FOR_PYTHON = defaultdict(fetch_packages_in_active_python)
_PARSED_SETUP_FILES = dict()


def python_module_available(mod):
    """Return true if the specified python module is available."""
    return subprocess.Popen(["python",
                             "-c",
                             "import {0}".format(mod)],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE).wait() == 0


def run_if_module_unavailable(module,  # suppress(unused-function)
                              function,
                              *args,
                              **kwargs):
    """Run function if the module specified is not available."""
    if not python_module_available(module):
        return function(*args, **kwargs)

    return None


def python_is_pypy(version_string):  # suppress(unused-function)
    """Return true if the currently selected python is a PyPy python."""
    return "PyPy" in version_string


def _packages_to_install(installed, requested):
    """Return a list of packages to install.

    Already installed packages are skipped. Things like command line
    options will implicitly pass right through.
    """
    def real_identifier(requested_package):
        """Return egg component of package string."""
        if "#egg=" in requested_package:
            return requested_package.split("#egg=")[1]

        return requested_package

    # suppress(too-many-return-statements)
    def out_of_date(requested, installed):
        """Return true if requested is out of date."""
        if not installed:
            return True

        installed = LooseVersion(installed)

        if "==" in requested:
            return LooseVersion(requested.split("==")[1]) != installed
        elif ">=" in requested:
            return installed < LooseVersion(requested.split(">=")[1])
        elif ">" in requested:
            return installed <= LooseVersion(requested.split(">")[1])
        elif "<=" in requested:
            return installed > LooseVersion(requested.split("<=")[1])
        elif "<" in requested:
            return installed >= LooseVersion(requested.split("<")[1])

        return False

    # Do some simple version checks
    version_symbols_regex = r">|>=|==|<=|<"
    pkgs = [r for r in requested
            if out_of_date(real_identifier(r),
                           installed.get(re.split(version_symbols_regex,
                                                  real_identifier(r))[0]))]

    return list(set(pkgs))


def _upgrade_pip(cont, util):
    """Upgrade pip installation in current virtual environment."""
    pip = util.which("pip")
    if not os.environ.get("_POLYSQUARE_CHECKED_PIP_VERSION_" + pip, None):
        os.environ["_POLYSQUARE_CHECKED_PIP_VERSION_" + pip] = "True"
    else:
        return

    try:
        version = subprocess.check_output([util.which("pip"),
                                           "--disable-pip-version-check",
                                           "--version"],
                                          stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        # Try again without the version check argument - it could
        # not be disabled on some older versions of pip
        version = subprocess.check_output([util.which("pip"),
                                           "--version"])

    version = version.split()[1].decode()

    if LooseVersion(version) < LooseVersion("9.0.1"):
        arguments = [
            "python",
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip"
        ]

        if LooseVersion(version) > LooseVersion("6.0.3"):
            arguments.append("--disable-pip-version-check")

        util.execute(cont,
                     util.long_running_suppressed_output(),
                     *arguments)


def _pip_install_internal(container, util, py_path, pip_args=None, **kwargs):
    """Run pip install, without removing redundant packages."""
    pip_install_args = [
        container,
        util.long_running_suppressed_output(),
        "pip",
        "install",
        "--disable-pip-version-check"
    ] + (pip_args or list())

    allow_external = kwargs.pop("polysquare_allow_external", None) or list()
    if len(allow_external):
        pip_install_args = (pip_install_args[:4] +
                            ["--process-dependency-links"] +
                            list(*(chain([["--allow-external", a]
                                          for a in allow_external]))) +
                            pip_install_args[4:])

    util.execute(*pip_install_args,
                 instant_fail=kwargs.pop("instant_fail", True),
                 **kwargs)
    _PACKAGES_FOR_PYTHON[py_path] = fetch_packages_in_active_python()


def pip_install(container, util, *args, **kwargs):
    """Install packages listed in args with pip.

    This function does caching to make sure that we don't double-download
    packages.
    """
    _upgrade_pip(container, util)

    active_python = util.which("python")
    to_install = _packages_to_install(_PACKAGES_FOR_PYTHON[active_python],
                                      list(args))

    if len([p for p in to_install if not p.startswith("-")]):
        _pip_install_internal(container,
                              util,
                              active_python,
                              pip_args=to_install,
                              **kwargs)


def _parse_setup_py(container, py_path, fields):
    """Parse /setup.py and return its keyword arguments."""
    key = hashlib.sha1((os.path.join(os.getcwd(), "setup.py") +
                        py_path +
                        "".join(fields)).encode("utf-8")).hexdigest()
    try:
        return _PARSED_SETUP_FILES[key]
    except KeyError:  # suppress(pointless-except)
        pass

    parse_setup_py = container.fetch_script("parse_setup.py")
    fields_stream = subprocess.Popen(["python",
                                     parse_setup_py.fs_path] + list(fields),
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE).communicate()[0]
    parsed_fields = json.loads(fields_stream.decode("utf-8").strip())

    # Remember result, as querying it takes a second.
    _PARSED_SETUP_FILES[key] = parsed_fields
    return parsed_fields


def _parse_requirements_file(py_path):
    """Parse /requirements.txt and return a list of dependencies from it."""
    requirements_path = os.path.join(os.getcwd(), "requirements.txt")
    key = hashlib.sha1((requirements_path +
                        py_path).encode("utf-8")).hexdigest()

    try:
        return _PARSED_SETUP_FILES[key]
    except KeyError:  # suppress(pointless-except)
        pass

    try:
        with open(requirements_path, "r") as requirements_file:
            _PARSED_SETUP_FILES[key] = requirements_file.read().splitlines()
    except IOError:  # suppress(pointless-except)
        _PARSED_SETUP_FILES[key] = []

    return _PARSED_SETUP_FILES[key]


def _dependencies_to_update(container, py_path, installed, target):
    """Return a list of dependencies to install."""
    fields = ("extras_require",
              "install_requires",
              "setup_requires",
              "test_requires")
    parsed_setup_py = _parse_setup_py(container, py_path, fields)

    requested = parsed_setup_py.get("extras_require", dict()).get(target,
                                                                  list())
    requested += parsed_setup_py.get("install_requires", list())
    requested += parsed_setup_py.get("setup_requires", list())
    requested += parsed_setup_py.get("test_requires", list())
    requested += _parse_requirements_file(py_path)

    return _packages_to_install(installed, requested)


def pip_install_deps(cont, util, target, *args, **kwargs):
    """Install dependencies using pip.

    Dependencies are not installed if we've already got them installed. We
    use a shortcut method to determine that.
    """
    _upgrade_pip(cont, util)

    active_python = util.which("python")
    initially_installed_packages = _PACKAGES_FOR_PYTHON[active_python]

    to_install = _dependencies_to_update(cont,
                                         util.which("python"),
                                         initially_installed_packages,
                                         target)
    to_install += _packages_to_install(initially_installed_packages,
                                       list(args))

    pip_install_kwargs = {
        "pip_args": to_install
    }
    pip_install_kwargs.update(kwargs)

    if len([p for p in to_install if not p.startswith("-")]):
        _pip_install_internal(cont, util, active_python, **pip_install_kwargs)
