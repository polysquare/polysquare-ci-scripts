# /ciscripts/deploy/bii/deploy.py
#
# Copy directories into place to prepare for publishing biicode project
#
# See /LICENCE.md for Copyright information
"""Place a symbolic link of pandoc in a writable directory in PATH."""

import errno

import os

import shutil


def _move_directories_ignore_errors(directories, src, dst):
    """Move specified directories from :src: to :dst: ignoring errors."""
    for name in directories:
        try:
            os.rename(os.path.join(src, name),
                      os.path.join(dst, name))
        except OSError as error:
            if error.errno != errno.ENOENT:
                raise error


_BII_LAYOUT = [
    "bii",
    "bin",
    "lib",
    "blocks",
    "build"
]


def _get_bii_container(cont, util, shell):
    """Get pre-installed bii installation."""
    return cont.fetch_and_import("setup/project/configure_bii.py").get(cont,
                                                                       util,
                                                                       shell,
                                                                       None)


def run(cont, util, shell, argv=None):
    """Place a symbolic link of pandoc in a writable directory in PATH."""
    del argv

    cont.fetch_and_import("deploy/project/deploy.py").run(cont,
                                                          util,
                                                          shell)

    with util.Task("""Preparing for deployment to biicode"""):
        if os.environ.get("CI", None):
            build = cont.named_cache_dir("cmake-build", ephemeral=False)
            _move_directories_ignore_errors(_BII_LAYOUT, build, os.getcwd())

            if not util.which("bii"):
                path = util.find_usable_path_in_homedir(cont)
                with _get_bii_container(cont, util, shell).activated(util):
                    bii_binary = util.which("bii")
                destination = os.path.join(path, "pandoc")
                with util.Task("""Copying bii binary from """
                               """{0} to {1}.""".format(bii_binary,
                                                        destination)):
                    shutil.copy(bii_binary, destination)
