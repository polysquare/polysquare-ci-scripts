# /ciscripts/coverage/bii/coverage.py
#
# Submit coverage totals for a bii project to coveralls
#
# See /LICENCE.md for Copyright information
"""Submit coverage totals for a bii project to coveralls."""

import errno

import os

from contextlib import contextmanager


@contextmanager
def _bii_deps_in_place(cont):
    """Move bii project dependencies into layout.

    The coverage step may require these dependencies to be present.
    """
    bii_dir = os.path.join(cont.named_cache_dir("cmake-build"), "bii")
    try:
        os.rename(bii_dir, os.path.join(os.getcwd(), "bii"))
    except OSError as error:
        if error.errno != errno.ENOENT:
            raise error


def run(cont, util, shell, argv=None):
    """Submit coverage total to coveralls, with bii specific preparation."""
    with _bii_deps_in_place(cont):
        util.fetch_and_import("coverage/cmake/coverage.py").run(cont,
                                                                util,
                                                                shell,
                                                                argv)
