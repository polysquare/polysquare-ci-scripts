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
def _get_python_version_from_specified(python_executable, precision):
    """Get python version at precision from specified python_executable."""
    output = subprocess.Popen([python_executable, "--version"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).communicate()
    version = "".join([o.decode() for o in output])
    return ".".join(version.split(" ")[1].split(".")[0:precision]).strip()


def get_python_version(util, precision):  # suppress(unused-function)
    """Get python version at precision.

    1 gets the major version, 2 gets major and minor, 3 gets the patch version.
    Use distutils' version comparison functions to compare between versions.

    Note that on some implementations of python the version output comes
    through on stdout, on others it comes through on stderr. Just join them
    both and parse the whole string.
    """
    return _get_python_version_from_specified(util.which("python"), precision)


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

        _KNOWN_PYTHON_INSTALLATIONS.update({
            _get_python_version_from_specified(p, 3): p for p in candidates
        })

    return _KNOWN_PYTHON_INSTALLATIONS


def fetch_packages_in_active_python():
    """Fetch a dict of installed packages for the current python.

    The dict shall have the format { "package": "version" }.
    """
    out = subprocess.check_output(["pip", "list"]).decode().splitlines()
    reg = r"\(|\)|,|\s+"
    tuples = [[w for w in re.split(reg, l) if w][:2] for l in out]
    return dict([tuple(t) for t in tuples])

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


def python_is_pypy():  # suppress(unused-function)
    """Return true if the currently selected python is a PyPy python."""
    return "PyPy" in subprocess.Popen(["python", "--version"],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE).communicate()[1]


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

    version = subprocess.check_output([util.which("pip"),
                                       "--version"]).split()[1].decode()

    if LooseVersion(version) < LooseVersion("7.1.2"):
        util.execute(cont,
                     util.long_running_suppressed_output(),
                     "python",
                     "-m",
                     "pip",
                     "install",
                     "--upgrade",
                     "--disable-pip-version-check",
                     "pip")


def _pip_install_internal(container, util, py_path, *args, **kwargs):
    """Run pip install, without removing redundant packages."""
    pip_install_args = [
        container,
        util.long_running_suppressed_output(),
        "pip",
        "install",
        "--disable-pip-version-check"
    ] + list(args)

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
                              *to_install,
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

    return _packages_to_install(installed, requested)


def pip_install_deps(cont, util, target, *args, **kwargs):
    """Install dependencies using pip.

    Dependencies are not installed if we've already got them installed. We
    use a shortcut method to determine that.
    """
    _upgrade_pip(cont, util)

    active_python = util.which("python")
    initially_installed_packages = _PACKAGES_FOR_PYTHON[active_python]
    pip_install_args = [
        cont,
        util,
        active_python
    ]

    to_install = (_dependencies_to_update(cont,
                                          util.which("python"),
                                          initially_installed_packages,
                                          target) +
                  _packages_to_install(initially_installed_packages,
                                       list(args)))

    if len([p for p in to_install if not p.startswith("-")]):
        _pip_install_internal(*(pip_install_args + to_install), **kwargs)
