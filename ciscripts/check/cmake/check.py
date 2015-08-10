# /ciscripts/check/cmake/check.py
#
# Run tests and static analysis checks on a cmake project.
#
# See /LICENCE.md for Copyright information
"""Run tests and static analysis checks on a cmake project."""

import argparse

import os

import platform

import shutil

import subprocess

import tempfile

from collections import defaultdict

from contextlib import contextmanager


def _get_python_container(cont, util, shell):
    """Get python container to run linters in."""
    config_python = "setup/project/configure_python.py"
    python_ver = defaultdict(lambda: "3.4.1")
    return cont.fetch_and_import(config_python).get(cont,
                                                    util,
                                                    shell,
                                                    python_ver)


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

        with _get_python_container(cont, util, None).activated(util):
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


def _configure_cmake_project(cont,  # suppress(too-many-arguments)
                             util,
                             os_cont,
                             project_dir,
                             build_dir,
                             configure_cmd,
                             generator,
                             cmake_coverage):
    """Configure an underlying cmake project."""
    cmake_args = list(configure_cmd) + [
        project_dir,
        "-DCMAKE_COLOR_MAKEFILE=ON"
    ]

    if generator:
        cmake_args.append("-G" + generator)
    elif platform.system() == "Windows" and util.which("sh"):
        # If /sh.exe is installed on Windows, then default to
        # VS 2013, since MinGW Makefiles are broken where
        # sh is in the PATH.
        cmake_args.append("-GVisual Studio 12 2013")

    if cmake_coverage:
        tracefile = os.path.join(build_dir, "coverage.trace")
        cmake_args.append("-DCMAKE_UNIT_COVERAGE_FILE=" + tracefile)
        cmake_args.append("-DCMAKE_UNIT_TRACE_CONVERTER_LOCATION_OUTPUT=" +
                          os.path.join(build_dir, "TracefileConverterLoc"))

    os_cont.execute(cont,
                    util.running_output,
                    *cmake_args)


def reset_mtime(path):
    """Reset modification time of file at path."""
    os.utime(path, (1, 1))


def _parse_args(kind, argv):
    """Return parsed arguments for check_cmake_like_project."""
    parser = argparse.ArgumentParser(description="""Run {} """
                                                 """checks""".format(kind))
    parser.add_argument("--use-cmake-coverage",
                        help="""Generate coverage reports on cmake files""",
                        action="store_true")
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
    return parser.parse_known_args(argv or list())[0]


@contextmanager
def in_temp_dir():
    """Enter temporary directory."""
    current_dir = os.getcwd()
    temp_dir = tempfile.mkdtemp()
    try:
        os.chdir(temp_dir)
        yield
    finally:
        os.chdir(current_dir)
        shutil.rmtree(temp_dir)


def _get_variables_for_vs_path(path):
    """Get environment variables corresponding to Visual Studio install."""
    with in_temp_dir():
        print_vs_vars_filename = os.path.join(os.getcwd(),
                                              "print_vs_vars.bat")
        with open(print_vs_vars_filename, "w") as print_vs_vars:
            script = ("@call \"{}\"\n"
                      "@echo PATH=%PATH%\n"
                      "@echo INCLUDE=%INCLUDE%\n"
                      "@echo LIB=%LIB%\n"
                      "@echo LIBPATH=%LIBPATH%\n").format(path)
            print_vs_vars.write(script)

        stdout = subprocess.check_output(["cmd",
                                          "/c",
                                          print_vs_vars_filename])
        return dict([tuple(l.split("="))
                     for l in stdout.decode().splitlines()
                     if "=" in l])


def get_variables_for_vs_version(version):
    """Get environment variables corresponding to Visual Studio version."""
    base = "C:/{}/Microsoft Visual Studio {}/Common7/Tools/vsvars32.bat"
    candidates = (base.format("Program Files (x86)", version),
                  base.format("Program Files", version))
    for candidate in candidates:
        if os.path.exists(candidate):
            return _get_variables_for_vs_path(candidate)

    raise RuntimeError("""Visual Studio version {} """
                       """is not installed""".format(version))


@contextmanager
def _cmake_generator_context(user_configure_context,
                             util,
                             build,
                             generator):
    """Set up environment variables to configure, build and test project."""
    generator_environments = {
        "Visual Studio 14 2015": lambda: get_variables_for_vs_version("14.0"),
        "Visual Studio 12 2013": lambda: get_variables_for_vs_version("12.0"),
        "Visual Studio 11 2012": lambda: get_variables_for_vs_version("11.0"),
        "Visual Studio 10 2010": lambda: get_variables_for_vs_version("10.0"),
        "NMake Makefiles": lambda: get_variables_for_vs_version("12.0")
    }

    with user_configure_context(util, build):
        if platform.system() == "Windows" and util.which("sh"):
            # If /sh.exe is installed on Windows, then default to
            # VS 2013, since MinGW Makefiles are broken where
            # sh is in the PATH.
            generator = "Visual Studio 12 2013"

        try:
            update_variables = generator_environments[generator]()
        except KeyError:
            update_variables = dict()

        environ_copy = os.environ.copy()
        try:
            os.environ.update(update_variables)
            yield generator
        finally:
            os.environ = environ_copy


# suppress(too-many-arguments,too-many-locals)
def check_cmake_like_project(cont,
                             util,
                             shell,
                             kind="cmake",
                             after_lint=lambda cont, osc, util, build: None,
                             configure_context=lambda u, b: u.in_dir(b),
                             configure_cmd=("cmake", ),
                             test_cmd=("ctest", ),
                             build_cmd=lambda b: ("cmake", "--build", b),
                             after_test=lambda cont, util, build: None,
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
    result = _parse_args(kind, argv)
    os_cont = cont.fetch_and_import("setup/project/configure_os.py").get(cont,
                                                                         util,
                                                                         shell,
                                                                         None)

    with util.Task("""Checking {} project style guide """
                   """compliance""".format(kind)):
        _run_style_guide_lint(cont,
                              util,
                              result.lint_exclude or list(),
                              result.no_mdl)

    with util.Task("""Linting {} project""".format(kind)):
        _lint_cmake_files(cont,
                          util,
                          result.cmake_namespace,
                          result.lint_exclude or list())

    build_dir = cont.named_cache_dir("cmake-build", ephemeral=False)
    project_dir = os.getcwd()

    after_lint(cont, os_cont, util, build_dir)

    with _cmake_generator_context(configure_context,
                                  util,
                                  build_dir,
                                  result.generator) as generator:
        with util.Task("""Configuring {} project""".format(kind)):
            _configure_cmake_project(cont,
                                     util,
                                     os_cont,
                                     project_dir,
                                     build_dir,
                                     configure_cmd,
                                     generator,
                                     result.use_cmake_coverage)

        with util.Task("""Building {} project""".format(kind)):
            os_cont.execute(cont,
                            util.running_output,
                            *(build_cmd(build_dir)))

        with util.Task("""Testing {} project""".format(kind)):
            os_cont.execute(cont,
                            util.running_output,
                            *(tuple(list(test_cmd) + [
                                "--output-on-failure",
                                "-C",
                                "Debug"
                            ])))

        after_test(cont, util, build_dir)


NO_CACHE_FILE_PATTERNS = [
    "*/CMakeFiles/*",
    "*/DRIVER.error",
    "*/DRIVER.output",
    "*/Makefile",
    "*/Testing/*",
    "cmake_install.cmake",
    "CMakeCache.cmake",
    "CTestTestfile.cmake",
    "DartConfiguration.tcl"
]


def run(cont, util, shell, argv=None):
    """Run checks on this cmake project."""
    def _after_test(cont, util, build):
        """Reset modification time of files we don't want to cache."""
        del cont

        with util.Task("""Preliminary cleanup of cmake project"""):
            util.apply_to_files(reset_mtime,
                                build,
                                matching=NO_CACHE_FILE_PATTERNS)

    check_cmake_like_project(cont,
                             util,
                             shell,
                             kind="cmake",
                             after_test=_after_test,
                             argv=argv)
