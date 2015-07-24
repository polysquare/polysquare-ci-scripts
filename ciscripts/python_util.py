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

import os

import re

import subprocess

import warnings

from collections import defaultdict

from contextlib import contextmanager

from distutils.version import LooseVersion

from itertools import chain


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


def get_python_version(precision):  # suppress(unused-function)
    """Get python version at precision.

    1 gets the major version, 2 gets major and minor, 3 gets the patch version.
    Use distutils' version comparison functions to compare between versions.

    Note that on some implementations of python the version output comes
    through on stdout, on others it comes through on stderr. Just join them
    both and parse the whole string.
    """
    output = subprocess.Popen(["python", "--version"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).communicate()
    version = "".join([o.decode() for o in output])
    return ".".join(version.split(" ")[1].split(".")[0:precision]).strip()


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
            return installed > LooseVersion(requested.split(">=")[1])
        elif "<" in requested:
            return installed >= LooseVersion(requested.split(">")[1])

        return False

    # Do some simple version checks
    version_symbols_regex = r">|>=|==|<=|<"
    pkgs = [r for r in requested
            if out_of_date(real_identifier(r),
                           installed.get(re.split(version_symbols_regex,
                                                  real_identifier(r))[0]))]

    return list(set(pkgs))


def _pip_install_internal(container, util, pip_path, *args, **kwargs):
    """Run pip install, without removing redundant packages."""
    pip_install_args = [
        container,
        util.long_running_suppressed_output(),
        "pip",
        "install",
        "--download-cache",
        container.named_cache_dir("pip-cache")
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
    _PACKAGES_FOR_PYTHON[pip_path] = fetch_packages_in_active_python()


def pip_install(container, util, *args, **kwargs):
    """Install packages listed in args with pip.

    This function does caching to make sure that we don't double-download
    packages.
    """
    active_python = util.which("python")
    to_install = _packages_to_install(_PACKAGES_FOR_PYTHON[active_python],
                                      list(args))

    if len([p for p in to_install if not p.startswith("-")]):
        _pip_install_internal(container,
                              util,
                              active_python,
                              *to_install,
                              **kwargs)


def _parse_setup_py():
    """Parse /setup.py and return its keyword arguments."""
    current_setup_py = os.path.join(os.getcwd(), "setup.py")
    try:
        return _PARSED_SETUP_FILES[current_setup_py]
    except KeyError:  # suppress(pointless-except)
        pass

    setuptools_arguments = dict()

    @contextmanager
    def patched_setuptools():
        """Import setuptools and patch it."""
        import setuptools

        def setup_hook(*args, **kwargs):
            """Hook the setup function and log its arguments."""
            del args

            setuptools_arguments.update(kwargs)

        old_setup = setuptools.setup
        setuptools.setup = setup_hook

        try:
            yield
        finally:
            setuptools.setup = old_setup

    with patched_setuptools():
        import imp
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            imp.load_source("setup.py", current_setup_py)

    # Remember result, as querying it takes a second.
    _PARSED_SETUP_FILES[current_setup_py] = setuptools_arguments
    return setuptools_arguments


def _dependencies_to_update(installed, target):
    """Return a list of dependencies to install."""
    requested = _parse_setup_py().get("extras_require", dict()).get(target,
                                                                    dict())

    return _packages_to_install(installed, requested)


def pip_install_deps(cont, util, target, *args, **kwargs):
    """Install dependencies using pip.

    Dependencies are not installed if we've already got them installed. We
    use a shortcut method to determine that.
    """
    active_python = util.which("python")
    initially_installed_packages = _PACKAGES_FOR_PYTHON[active_python]
    pip_install_args = [
        cont,
        util,
        active_python
    ]

    to_install = (_dependencies_to_update(initially_installed_packages,
                                          target) +
                  _packages_to_install(initially_installed_packages,
                                       list(args)))

    if len([p for p in to_install if not p.startswith("-")]):
        _pip_install_internal(*(pip_install_args + to_install), **kwargs)
