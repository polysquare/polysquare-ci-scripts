# /ciscripts/check/conan/check.py
#
# Run tests and static analysis checks on a conan project.
#
# See /LICENCE.md for Copyright information
"""Run tests and static analysis checks on a conan project."""

import argparse

import errno

import os

from contextlib import contextmanager


def _get_python_container(cont, util, shell):
    """Get a python 3 installation."""
    py_ver = util.language_version("python3")
    config_python = "setup/project/configure_python.py"
    return cont.fetch_and_import(config_python).get(cont,
                                                    util,
                                                    shell,
                                                    py_ver)


def _get_ruby_container(cont, util, shell):
    """Get a ruby installation."""
    rb_ver = util.language_version("ruby")
    config_ruby = "setup/project/configure_ruby.py"
    return cont.fetch_and_import(config_ruby).get(cont, util, shell, rb_ver)


def _get_conan_container(cont, util, shell):
    """Get conan container."""
    configure_conan = "setup/project/configure_conan.py"
    return cont.fetch_and_import(configure_conan).get(cont, util, shell, None)


_CONAN_LAYOUT = [
    "build"
]


# suppress(too-many-locals)
def run(cont, util, shell, argv=None, override_kwargs=None):
    """Run checks on this conan project."""
    parser = argparse.ArgumentParser(description="""Run conan checks""")
    parser.add_argument("--lint-exclude",
                        nargs="*",
                        type=str,
                        help="""Patterns of files to exclude from linting""")
    result, remainder = parser.parse_known_args(argv or list())

    cmake_check = cont.fetch_and_import("check/cmake/check.py")

    py_cont = _get_python_container(cont, util, shell)
    rb_cont = _get_ruby_container(cont, util, shell)
    conan_cont = _get_conan_container(cont, util, shell)

    def _after_lint(cont, os_cont, util):
        """Perform conan specific setup."""
        with py_cont.activated(util), conan_cont.activated(util):
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

    @contextmanager
    def _configure_context(util):
        """Activate other language containers we might have available."""
        build_dir = os.path.join(os.getcwd(), "build")
        try:
            os.makedirs(build_dir)
        except OSError as error:
            if error.errno != errno.EEXIST:
                raise error

        with util.in_dir(build_dir):
            with py_cont.activated(util), rb_cont.activated(util):
                yield build_dir

    kwargs = {
        "kind": "conan",
        "build_tree": _CONAN_LAYOUT,
        "after_lint": _after_lint,
        "after_test": _after_test,
        "configure_context": _configure_context
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
