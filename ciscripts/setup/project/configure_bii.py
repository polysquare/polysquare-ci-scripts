# /ciscripts/setup/project/configure_bii.py
#
# A script which configures and activates a bii installation
#
# See /LICENCE.md for Copyright information
"""A script which configures and activates a bii installation."""

import os
import os.path

import platform

import shutil

from collections import defaultdict


def get(container, util, shell, ver_info):
    """Return a BiiContainer for an installed bii in container."""
    del util
    del ver_info

    version = "latest"

    # This class is intended to be used through LanguageBase, so
    # most of its methods are private
    #
    # suppress(too-few-public-methods)
    class BiiContainer(container.new_container_for("bii", version)):

        """A container representing an active bii installation."""

        # pylint can't detect that this is a new-style class
        #
        # suppress(super-on-old-class)
        def __init__(self, version, installation, shell):
            """Initialize a bii container for this version."""
            super(BiiContainer, self).__init__(installation,
                                               "bii",
                                               version,
                                               shell)
            assert os.path.exists(self._installation)

        # suppress(super-on-old-class)
        def clean(self, util_mod):
            """Clean out cruft in the container."""
            super(BiiContainer, self).clean(util_mod)

        def _active_environment(self, tuple_type):
            """Return active environment for bii container."""
            env_to_overwrite = dict()
            env_to_prepend = {
                "PATH": os.path.join(self._installation, "bin")
            }

            return tuple_type(overwrite=env_to_overwrite,
                              prepend=env_to_prepend)

    return BiiContainer(version, container.language_dir("bii"), shell)


_BII_SCRIPT = ("#!/usr/bin/env python\n"
               "import sys, os\n"
               "\n"
               "biicode_repo_path = '{}'\n"
               "\n"
               "sys.path.append(os.path.join(biicode_repo_path))\n"
               "from biicode.client.shell.bii import main\n"
               "main(sys.argv[1:])")


def run(container, util, shell, ver_info):
    """Install and activates a bii installation.

    This function returns a BiiContainer, which has a path
    and keeps a reference to its parent container.
    """
    config_python = "setup/project/configure_python.py"

    py_ver = defaultdict(lambda: "3.4.1")
    container.fetch_and_import("python_util.py")
    container.fetch_and_import(config_python).run(container,
                                                  util,
                                                  shell,
                                                  py_ver)

    bii_dir = container.language_dir("bii")
    bii_bin = os.path.join(bii_dir, "bin")

    if platform.system() == "Windows":
        bii_script_filename = os.path.join(bii_bin, "bii.exe")
    else:
        bii_script_filename = os.path.join(bii_bin, "bii")

    if not os.path.exists(bii_script_filename):
        shutil.rmtree(bii_dir)
        os.makedirs(bii_dir)
        with util.in_dir(bii_dir):
            biicode_repo = os.path.join(bii_dir, "biicode")
            with util.Task("""Downloading biicode client"""):
                remote = "git://github.com/biicode/biicode"
                util.execute(container,
                             util.long_running_suppressed_output(),
                             "git",
                             "clone",
                             remote,
                             instant_fail=True)
                with util.in_dir(biicode_repo):
                    util.execute(container,
                                 util.output_on_fail,
                                 "git",
                                 "submodule",
                                 "update",
                                 "--init",
                                 "--recursive",
                                 instant_fail=True)
                    os.makedirs(bii_bin)
                    shutil.rmtree(os.path.join(biicode_repo, "client", "test"))
                    shutil.rmtree(os.path.join(biicode_repo, "common", "test"))
                    with open(bii_script_filename, "w") as bii_scr:
                        escaped_bii_dir = bii_dir.replace("\\", "/")
                        bii_scr.write(_BII_SCRIPT.format(escaped_bii_dir))
                    util.make_executable(bii_script_filename)
                    util.execute(container,
                                 util.long_running_suppressed_output(),
                                 "pip",
                                 "install",
                                 "-r",
                                 os.path.join(biicode_repo,
                                              "common",
                                              "requirements.txt"),
                                 instant_fail=True)
                    util.execute(container,
                                 util.long_running_suppressed_output(),
                                 "pip",
                                 "install",
                                 "-r",
                                 os.path.join(biicode_repo,
                                              "client",
                                              "requirements.txt"),
                                 instant_fail=True)

            # Deleting the git directory causes PermissionError on Windows
            if platform.system() != "Windows":
                shutil.rmtree(os.path.join(biicode_repo, ".git"))
                os.remove(os.path.join(biicode_repo, "client", ".git"))
                os.remove(os.path.join(biicode_repo, "common", ".git"))

    with util.Task("""Activating biicode"""):
        bii_container = get(container, util, shell, ver_info)
        bii_container.activate(util)
        return bii_container
