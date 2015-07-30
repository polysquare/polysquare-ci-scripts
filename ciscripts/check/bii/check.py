# /ciscripts/check/bii/check.py
#
# Run tests and static analysis checks on a bii project.
#
# See /LICENCE.md for Copyright information
"""Run tests and static analysis checks on a bii project."""

import argparse

import errno

import os

import shutil

from collections import defaultdict

from contextlib import contextmanager


def _move_directories_ignore_errors(directories, src, dst):
    """Move specified directories from :src: to :dst: ignoring errors."""
    for name in directories:
        try:
            os.rename(os.path.join(src, name),
                      os.path.join(dst, name))
        except OSError as error:
            if error.errno != errno.ENOENT:
                raise error


def _try_rmtree(path):
    """Attempt to remove tree at path, ignoring file not found errors."""
    try:
        shutil.rmtree(path)
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
    """Run checks on this bii project."""
    parser = argparse.ArgumentParser(description="""Run bii checks""")
    parser.add_argument("--block",
                        help="""Block name""",
                        type=str,
                        required=True)
    result, remainder = parser.parse_known_args(argv or list())

    cmake_check_script = "check/cmake/check.py"
    cmake_check = cont.fetch_and_import(cmake_check_script)

    def _after_lint(cont, os_cont, util, build):
        """Restore cached files and perform bii specific setup."""
        with util.Task("""Restoring cached files to build tree"""):
            _move_directories_ignore_errors(_BII_LAYOUT, build, os.getcwd())

        with util.Task("""Downloading dependencies"""):
            if not os.path.exists(os.path.join(os.getcwd(), "bii")):
                os_cont.execute(cont,
                                util.long_running_suppressed_output(),
                                "bii",
                                "init",
                                "-l")
            os_cont.execute(cont,
                            util.long_running_suppressed_output(),
                            "bii",
                            "find")

        with util.Task("""Initializing bii block"""):
            os_cont.execute(cont,
                            util.running_output,
                            "bii",
                            "new",
                            result.block)

    def _after_test(cont, util, build):
        """Restore build tree from bii layout to container caches."""
        del cont

        with util.Task("""Moving bii layout to cache"""):
            _try_rmtree(os.path.join(os.getcwd(), "cmake"))
            _move_directories_ignore_errors(_BII_LAYOUT, os.getcwd(), build)

        with util.Task("""Performing cleanup on cache"""):
            util.apply_to_files(cmake_check.reset_mtime,
                                build,
                                matching=[
                                    "*/.hive.db",
                                    "*/layout.bii"
                                ] + cmake_check.NO_CACHE_FILE_PATTERNS)

    @contextmanager
    def _no_context(util, build):
        """Stay in current directory."""
        del util
        del build

        try:
            yield
        finally:
            pass

    py_ver = defaultdict(lambda: "2.7.9")
    config_python = "setup/project/configure_python.py"
    py_cont = cont.fetch_and_import(config_python).run(cont,
                                                       util,
                                                       shell,
                                                       py_ver)

    with py_cont.activated(util):
        cmake_check.check_cmake_like_project(cont,
                                             util,
                                             shell,
                                             kind="bii",
                                             after_lint=_after_lint,
                                             configure_context=_no_context,
                                             configure_cmd=("bii",
                                                            "configure"),
                                             build_cmd=lambda _: ("bii",
                                                                  "build"),
                                             test_cmd=("bii", "test"),
                                             after_test=_after_test,
                                             argv=remainder)
