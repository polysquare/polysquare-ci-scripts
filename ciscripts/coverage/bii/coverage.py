# /ciscripts/coverage/bii/coverage.py
#
# Submit coverage totals for a bii project to coveralls
#
# See /LICENCE.md for Copyright information
"""Submit coverage totals for a bii project to coveralls."""

import errno

import os

from contextlib import contextmanager


def _move_ignore_enoent(src, dst):
    """Move src to dst, ignoring ENOENT."""
    try:
        os.rename(src, dst)
    except OSError as error:
        if error.errno != errno.ENOENT:
            raise error


@contextmanager
def _bii_deps_in_place(cont):
    """Move bii project dependencies into layout.

    The coverage step may require these dependencies to be present.
    """
    bii_dir = os.path.join(cont.named_cache_dir("cmake-build"), "bii")
    _move_ignore_enoent(bii_dir, os.path.join(os.getcwd(), "bii"))

    try:
        yield
    finally:
        _move_ignore_enoent(os.path.join(os.getcwd(), "bii"), bii_dir)


def run(cont, util, shell, argv=None):
    """Submit coverage total to coveralls, with bii specific preparation."""
    with _bii_deps_in_place(cont):
        util.fetch_and_import("coverage/cmake/coverage.py").run(cont,
                                                                util,
                                                                shell,
                                                                argv)
