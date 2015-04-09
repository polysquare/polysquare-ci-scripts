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
import subprocess


def get_python_version(precision):  # suppress(unused-function)
    """Get python version at precision.

    1 gets the major version, 2 gets major and minor, 3 gets the patch version.
    Use distutils' version comparison functions to compare between versions.
    """
    version = subprocess.Popen(["python", "--version"],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE).communicate()[1]
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


def pip_install(container, util, *args, **kwargs):
    """Install packages listed in args with pip.

    This function does caching to make sure that we don't double-download
    packages.
    """
    pip_install_args = [
        container,
        util.long_running_suppressed_output(),
        "pip",
        "install",
        "--download-cache",
        container.named_cache_dir("pip-cache")
    ] + list(args)

    util.execute(*pip_install_args, **kwargs)


def pip_install_deps(py_cont, util, target, *args, **kwargs):
    """Install dependencies using pip.

    Dependencies are not installed if they have already been installed for this
    project.
    """
    stampfile = os.path.join(py_cont.named_cache_dir("pip-setuptools"),
                             ".installed-{0}".format(target))

    if not os.path.exists(stampfile):
        pip_install_args = [
            py_cont,
            util,
            "-e",
            ".[{0}]".format(target)
        ] + list(args)

        pip_install(*pip_install_args, **kwargs)
