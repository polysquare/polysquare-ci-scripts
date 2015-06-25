# /ciscripts/check/cmake/check.py
#
# Run tests and static analysis checks on a cmake project.
#
# See /LICENCE.md for Copyright information
"""Run tests and static analysis checks on a cmake project."""

import argparse

import os


def _run_style_guide_lint(cont, util, lint_exclude, no_mdl):
    """Run /ciscripts/check/project/lint.py on this cmake project."""
    supps = [
        r"\bNOLINT[^\s]*\b",
        r"\bcppcheck-suppress=[^\s]*\b"
    ]
    excl = [
        os.path.join(os.getcwd(), "build", "*")
    ] + lint_exclude

    cont.fetch_and_import("check/project/lint.py").run(cont,
                                                       util,
                                                       None,
                                                       None,
                                                       no_mdl=no_mdl,
                                                       extensions=[
                                                           "cmake",
                                                           "CMakeLists.txt"
                                                       ],
                                                       exclusions=excl,
                                                       block_regexps=supps)


def _lint_cmake_files(cont, util, namespace, exclusions):
    """Run cmake specific linters on specified files."""
    files_to_lint = util.apply_to_files(lambda x: x,
                                        os.getcwd(),
                                        matching=[
                                            "*CMakeLists.txt",
                                            "*.cmake",
                                        ],
                                        not_matching=[
                                            os.path.join(cont.path(), "*"),
                                        ] + exclusions)

    if len(files_to_lint):
        polysquare_linter_args = files_to_lint + [
            "--indent",
            "4"
        ]

        if namespace:
            polysquare_linter_args.extend(["--namespace", namespace])

        util.execute(cont,
                     util.output_on_fail,
                     "polysquare-cmake-linter",
                     *polysquare_linter_args)

        # Set HOME to the user's actual base directory, since
        # cmakelint depends on it
        util.execute(cont,
                     util.output_on_fail,
                     "cmakelint",
                     "--filter=-whitespace/extra,-whitespace/indent",
                     *files_to_lint,
                     env={
                         "HOME": os.path.expanduser("~")
                     })


def _reset_mtime(path):
    """Reset modification time of file at path."""
    os.utime(path, (1, 1))


def run(cont,
        util,
        shell,
        argv=None):
    """Run tests and static analysis checks on this cmake project.

    This will run the generic project style guide checks on all cmake files
    and lint all markdown documentation. It then configures, builds and
    installs the cmake project.

    Pass --generator to specify a different buildsystem generator to
    use than the built-in one.

    Pass --coverage-exclude to exclude certain files from coverage
    report generation.

    Pass --lint-exclude to exclude certain files from being statically
    analyzed.
    """
    parser = argparse.ArgumentParser(description="""Run cmake checks""")
    parser.add_argument("--coverage-exclude",
                        nargs="*",
                        type=str,
                        help="""Patterns of files to exclude from coverage""")
    parser.add_argument("--lint-exclude",
                        nargs="*",
                        type=str,
                        help="""Patterns of files to exclude from linting""")
    parser.add_argument("--no-mdl",
                        help="""Don't run markdownlint""",
                        action="store_true")
    parser.add_argument("--cmake-namespace",
                        help="""Namespace of cmake functions""",
                        type=str)
    parser.add_argument("--generator",
                        help="""Generator to use """
                             """(defaults to system generator)""",
                        default=None,
                        type=str)
    result, _ = parser.parse_known_args(argv or list())

    config_os_container = "setup/project/configure_os.py"
    os_cont = cont.fetch_and_import(config_os_container).get(cont,
                                                             util,
                                                             shell,
                                                             None)

    with util.Task("""Checking cmake project style guide compliance"""):
        _run_style_guide_lint(cont,
                              util,
                              result.lint_exclude or list(),
                              result.no_mdl)

    with util.Task("""Linting cmake project"""):
        _lint_cmake_files(cont,
                          util,
                          result.cmake_namespace,
                          result.lint_exclude or list())

    build_dir = cont.named_cache_dir("cmake-build", ephemeral=False)
    project_dir = os.getcwd()

    with util.in_dir(build_dir):
        with util.Task("""Configuring cmake project"""):
            cmake_args = []

            if result.generator:
                cmake_args.append("-G" + result.generator)

            os_cont.execute(cont,
                            util.running_output,
                            "cmake",
                            "-DCMAKE_COLOR_MAKEFILE=ON",
                            project_dir,
                            *cmake_args)

        with util.Task("""Building cmake project"""):
            os_cont.execute(cont,
                            util.running_output,
                            "cmake",
                            "--build",
                            ".")

        with util.Task("""Testing cmake project"""):
            os_cont.execute(cont,
                            util.running_output,
                            "ctest",
                            "--output-on-failure",
                            "-C",
                            "Debug",
                            ".")

        with util.Task("""Preliminary cleanup of cmake project"""):
            util.apply_to_files(_reset_mtime,
                                build_dir,
                                matching=[
                                    "*/CMakeFiles/*",
                                    "*/DRIVER.error",
                                    "*/DRIVER.output",
                                    "*/Makefile",
                                    "*/Testing/*",
                                    "cmake_install.cmake",
                                    "CMakeCache.cmake",
                                    "CTestTestfile.cmake",
                                    "DartConfiguration.tcl",
                                ])
