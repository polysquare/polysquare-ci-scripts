# /ciscripts/check/bii/check.py
#
# Run tests and static analysis checks on a bii project.
#
# See /LICENCE.md for Copyright information
"""Run tests and static analysis checks on a bii project."""

import argparse

import os

import platform

import re

from collections import defaultdict

from contextlib import contextmanager


def _get_python_container(cont, util, shell):
    """Get a python 2.7.9 installation if necessary."""
    if platform.system() == "Linux":
        return None

    py_ver = defaultdict(lambda: "2.7.9")
    config_python = "setup/project/configure_python.py"
    return cont.fetch_and_import(config_python).get(cont,
                                                    util,
                                                    shell,
                                                    py_ver)


def _get_bii_container(cont, util, shell):
    """Get biicode container."""
    return cont.fetch_and_import("setup/project/configure_bii.py").get(cont,
                                                                       util,
                                                                       shell,
                                                                       None)


_BII_LAYOUT = [
    "bii",
    "bin",
    "lib",
    "blocks",
    "build"
]


@contextmanager
def _maybe_activate_python(py_cont, util):
    """Activate py_cont if it exists."""
    if py_cont:
        with py_cont.activated(util):
            yield
    else:
        yield


def _bii_run_build(util, bii_exe):
    """Return function to build a bii project."""
    def _win_safe_abs(path):
        """Get absolute path to file, but escape drive letters."""
        abs_path = os.path.abspath(path)
        if platform.system() == "Windows":
            abs_path = re.sub(r"([: ])", r"$\1", abs_path)
            abs_path = re.sub(r"\\", r"/", abs_path)

        return abs_path

    def _run_build_func(build):
        """Build the source code.

        At the moment, this involves a temporary hack on the ninja
        build file to remove all relative paths from targets.
        """
        del build

        bii_build = os.path.join(os.getcwd(), "bii", "build")
        ninja_file_path = os.path.join(bii_build, "build.ninja")
        if os.path.exists(ninja_file_path):
            with util.in_dir(bii_build):
                if os.path.exists(ninja_file_path):
                    with open(ninja_file_path, "r") as ninja_file:
                        ninja_contents = ninja_file.read()
                    write_lines = []
                    for line in ninja_contents.splitlines():
                        if line.startswith("build ../"):
                            parts = (len("build "), line.find(": C"))
                            line = (line[:parts[0]] +
                                    _win_safe_abs(line[parts[0]:parts[1]]) +
                                    line[parts[1]:])
                        write_lines.append(line)

                    with open(ninja_file_path, "w") as ninja_file:
                        ninja_file.write("\n".join(write_lines))
                        ninja_file.write("\n")

        return (bii_exe, "build")

    return _run_build_func


def run(cont, util, shell, argv=None):
    """Run checks on this bii project."""
    parser = argparse.ArgumentParser(description="""Run bii checks""")
    parser.add_argument("--block",
                        help="""Block name""",
                        type=str,
                        required=True)
    parser.add_argument("--lint-exclude",
                        nargs="*",
                        type=str,
                        help="""Patterns of files to exclude from linting""")
    result, remainder = parser.parse_known_args(argv or list())

    cmake_check_script = "check/cmake/check.py"
    cmake_check = cont.fetch_and_import(cmake_check_script)

    py_cont = _get_python_container(cont, util, shell)
    bii_cont = _get_bii_container(cont, util, shell)
    bii_exe = os.path.join(bii_cont.executable_path(), "bii")

    def _after_lint(cont, os_cont, util):
        """Perform bii specific setup."""
        with _maybe_activate_python(py_cont, util), bii_cont.activated(util):
            with util.Task("""Downloading dependencies"""):
                if not os.path.exists(os.path.join(os.getcwd(), "bii")):
                    os_cont.execute(cont,
                                    util.long_running_suppressed_output(),
                                    bii_exe,
                                    "init",
                                    "-l")
                os_cont.execute(cont,
                                util.long_running_suppressed_output(),
                                bii_exe,
                                "find")

            with util.Task("""Initializing bii block"""):
                os_cont.execute(cont,
                                util.running_output,
                                bii_exe,
                                "new",
                                result.block)

    def _after_test(cont, util, build):
        """Cleanup bii files in build caches."""
        del cont

        with util.Task("""Performing cleanup on cache"""):
            if not os.environ.get("POLYSQUARE_KEEP_CMAKE_CACHE", None):
                util.force_remove_tree(os.path.join(os.getcwd(), "cmake"))
            util.apply_to_files(cmake_check.reset_mtime,
                                build,
                                matching=[
                                    "*/.hive.db",
                                    "*/layout.bii"
                                ] + cmake_check.NO_CACHE_FILE_PATTERNS)

    @contextmanager
    def _activate_py27(util):
        """Stay in current directory."""
        with _maybe_activate_python(py_cont, util), bii_cont.activated(util):
            yield

    cmake_check.check_cmake_like_project(cont,
                                         util,
                                         shell,
                                         kind="bii",
                                         build_tree=_BII_LAYOUT,
                                         after_lint=_after_lint,
                                         configure_context=_activate_py27,
                                         configure_cmd=(bii_exe, "configure"),
                                         build_cmd=_bii_run_build(util,
                                                                  bii_exe),
                                         test_cmd=(bii_exe, "test"),
                                         after_test=_after_test,
                                         argv=(remainder +
                                               ["--lint-exclude",
                                                "*/bii/*"] +
                                               (result.lint_exclude or [])))
