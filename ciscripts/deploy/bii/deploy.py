# /ciscripts/deploy/bii/deploy.py
#
# Copy directories into place to prepare for publishing biicode project
#
# See /LICENCE.md for Copyright information
"""Place a symbolic link of pandoc in a writable directory in PATH."""

import errno

import os


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
