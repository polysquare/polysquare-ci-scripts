# /ciscripts/check/conan/check.py
#
# Run tests and static analysis checks on a conan project.
#
# See /LICENCE.md for Copyright information
"""Run tests and static analysis checks on a conan project."""

import argparse

import os


def _get_python_container(cont, util, shell):
    """Get a python 3 installation."""
    py_ver = util.language_version("python3")
    config_python = "setup/project/configure_python.py"
    return cont.fetch_and_import(config_python).get(cont,
                                                    util,
                                                    shell,
                                                    py_ver)


_CONAN_LAYOUT = [
    "build"
]


def run(cont, util, shell, argv=None, override_kwargs=None):
    """Run checks on this conan project."""
    parser = argparse.ArgumentParser(description="""Run conan checks""")
    parser.add_argument("--lint-exclude",
                        nargs="*",
                        type=str,
                        help="""Patterns of files to exclude from linting""")
    result, remainder = parser.parse_known_args(argv or list())

    cmake_check_script = "check/cmake/check.py"
    cmake_check = cont.fetch_and_import(cmake_check_script)

    py_cont = _get_python_container(cont, util, shell)

    def _after_lint(cont, os_cont, util):
        """Perform conan specific setup."""
        with py_cont.activated(util):
            with util.Task("""Downloading dependencies"""):
                os_cont.execute(cont,
                                util.running_output,
                                "conan",
                                "install",
                                "--build=missing")

    def _after_test(cont, util, build):
        """Cleanup conan files in build caches."""
        del cont

        with util.Task("""Performing cleanup on cache"""):
            util.apply_to_files(cmake_check.reset_mtime,
                                build,
                                matching=cmake_check.NO_CACHE_FILE_PATTERNS + [
                                    "conaninfo.txt",
                                    "conanbuildinfo.cmake",
                                ])
            util.force_remove_tree(os.path.join(os.getcwd(), "build"))

    kwargs = {
        "kind": "conan",
        "build_tree": _CONAN_LAYOUT,
        "after_lint": _after_lint,
        "after_test": _after_test
    }

    if override_kwargs:
        kwargs.update(override_kwargs)

    cmake_check.check_cmake_like_project(cont,
                                         util,
                                         shell,
                                         argv=(remainder +
                                               ["--lint-exclude",
                                                "*/conanbuildinfo.cmake",
                                                "*/conaninfo.txt"] +
                                               (result.lint_exclude or [])),
                                         **kwargs)
