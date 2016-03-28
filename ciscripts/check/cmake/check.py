# /ciscripts/check/cmake/check.py
#
# Run tests and static analysis checks on a cmake project.
#
# See /LICENCE.md for Copyright information
"""Run tests and static analysis checks on a cmake project."""

import argparse

import errno

import os

import platform

import shutil

import string

import subprocess

import tempfile

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


def _get_python_container(cont, util, shell):
    """Get python container to run linters in."""
    config_python = "setup/project/configure_python.py"
    py_ver = util.language_version("python3")
    return cont.fetch_and_import(config_python).get(cont,
                                                    util,
                                                    shell,
                                                    py_ver)


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
                                                           "cpp",
                                                           "c",
                                                           "h",
                                                           "hpp",
                                                           "cc",
                                                           "cxx",
                                                           "hxx",
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
                         "--filter=-whitespace/extra,"
                         "-whitespace/indent,"
                         "-package/consistency",
                         *files_to_lint,
                         env={
                             "HOME": os.path.expanduser("~")
                         })


def _generator_cache_is_stale(build_dir, generator):
    """Check if generator cache is stale and doesn't match generator."""
    try:
        with open(os.path.join(build_dir, "CMakeCache.txt")) as cmake_cache:
            key = "CMAKE_GENERATOR:INTERNAL="
            for line in cmake_cache.readlines():
                if (line.startswith(key) and
                        line.split(key)[1][:-1] != generator):
                    return True
    except IOError:  # suppress(pointless-except)
        pass

    return False


def _check_generator_cache(util, build_dir, generator):
    """Clear build cache if generator is different from cache."""
    if _generator_cache_is_stale(build_dir, generator):
        with util.Task("""Clearing stale generator cache"""):
            util.force_remove_tree(os.path.join(build_dir, "CMakeFiles"))
            os.remove(os.path.join(build_dir, "CMakeCache.txt"))


def _configure_cmake_project(cont,  # suppress(too-many-arguments)
                             util,
                             os_cont,
                             project_dir,
                             project_dir_xform,
                             build_dir_xform,
                             build_dir,
                             configure_context_dir,
                             configure_cmd,
                             generator,
                             cmake_coverage,
                             cmake_cache_variables):
    """Configure an underlying cmake project."""
    cmake_cache_variables = cmake_cache_variables or list()

    if cmake_coverage:
        tracefile = os.path.join(build_dir, "coverage.trace")
        converter = os.path.join(build_dir, "TracefileConverterLoc")
        cmake_cache_variables.extend(["{}={}".format(k, v) for k, v in {
            "CMAKE_UNIT_COVERAGE_FILE": tracefile,
            "CMAKE_UNIT_TRACE_CONVERTER_LOCATION_OUTPUT": converter
        }.items()])

    cmake_cache_variables.append("CMAKE_COLOR_MAKEFILE=ON")
    cmake_args = list(configure_cmd(project_dir)) + [
        project_dir_xform(project_dir)
    ] + ["-D{}".format(v) for v in cmake_cache_variables]

    if generator:
        cmake_args.append("-G" + generator)
    elif platform.system() == "Windows" and util.which("sh"):
        # If /sh.exe is installed on Windows, then default to
        # VS 2013, since MinGW Makefiles are broken where
        # sh is in the PATH.
        cmake_args.append("-GVisual Studio 12 2013")

    # We run the build_dir_xform on project_dir since we've moved
    # the build tree into place
    _check_generator_cache(util, build_dir_xform(project_dir), generator)

    os_cont.execute(cont,
                    util.running_output,
                    *cmake_args)

    # After running, change back into the current directory. Some build tools
    # (like biicode) will delete the build tree and re-enter it, which
    # invalidates the inode that we're currently in.
    os.chdir(configure_context_dir)


def reset_mtime(path):
    """Reset modification time of file at path."""
    try:
        os.utime(path, (1, 1))
    except OSError as error:
        if error.errno != errno.ENOENT:
            raise error


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
    parser.add_argument("--cmake-cache-variables",
                        help="""Variables in k=v format to pass to """
                             """cmake.""",
                        nargs="*",
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

        # stdout.decode needs to be explicitly converted
        # to str from unicode, as we pass it to subprocess
        # later and unicode is an invalid value type there.
        stdout = subprocess.check_output(["cmd",
                                          "/c",
                                          print_vs_vars_filename])
        return dict([tuple(l.split("="))
                     for l in str(stdout.decode()).splitlines()
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
def _maybe_map_to_drive_letter(project_dir):
    """Map current directory to drive letter."""
    if platform.system() == "Windows":
        # Get all uppercase letters in reverse and try to
        # substitute the current directory for each of them,
        # stopping when we find one that works.
        #
        # Note that we need to map the parent directory of
        # the source directory to a drive letter - there
        # are some tools that depend on having the name
        # of the source directory which won't work if
        # we're in some sort of file system root.
        project_dir_name = os.path.basename(project_dir)
        project_dir_parent = os.path.abspath(os.path.join(project_dir, ".."))
        letters = [a for a in string.ascii_uppercase[::-1]]
        index = 0
        with open(os.devnull, "w") as devnull:
            while True:
                if subprocess.call(["subst",
                                    letters[index] + ":",
                                    project_dir_parent],
                                   stdout=devnull,
                                   stderr=devnull) == 0:
                    break

                index += 1

            os.chdir(letters[index] + ":/" + project_dir_name)

            try:
                yield os.getcwd()
            finally:
                os.chdir(project_dir)
                subprocess.check_call(["subst",
                                       "/D",
                                       letters[index] + ":"],
                                      stdout=devnull,
                                      stderr=devnull)
    else:
        yield os.getcwd()


@contextmanager
def _cmake_generator_context(util, generator):
    """Set up environment variables to configure, build and test project."""
    generator_environments = {
        "Visual Studio 14 2015": lambda: get_variables_for_vs_version("14.0"),
        "Visual Studio 12 2013": lambda: get_variables_for_vs_version("12.0"),
        "Visual Studio 11 2012": lambda: get_variables_for_vs_version("11.0"),
        "Visual Studio 10 2010": lambda: get_variables_for_vs_version("10.0"),
        "NMake Makefiles": lambda: get_variables_for_vs_version("12.0")
    }

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


@contextmanager
def _cmake_only_configure_context(util):
    """Enter real build directory."""
    build_dir = os.path.join(os.getcwd(), "build")
    try:
        os.makedirs(build_dir)
    except OSError as error:
        if error.errno != errno.EEXIST:
            raise error

    with util.in_dir(build_dir):
        yield build_dir


def _cmake_only_build_command(build):
    """Build command for a cmake-only project."""
    return ("cmake", "--build", os.path.join(build, "build"))


def _clean_coverage_files(util):
    """Clean coverage data from last build."""
    for coverage_file_path in ("coverage.info",
                               "coverage.trace",
                               "TracefileConverterLoc"):
        util.force_remove_tree(coverage_file_path)


def _default_during_test(*args, **kwargs):
    """No-op function."""
    del args
    del kwargs


# suppress(too-many-arguments,too-many-locals)
def check_cmake_like_project(cont,
                             util,
                             shell,
                             kind="cmake",
                             after_lint=lambda cont, osc, util: None,
                             build_tree=None,
                             configure_context=_cmake_only_configure_context,
                             configure_cmd=lambda b: ("cmake", ),
                             project_dir_xform=lambda d: d,
                             build_dir_xform=lambda d: os.path.join(d,
                                                                    "build"),
                             test_cmd=("ctest", ),
                             build_cmd=_cmake_only_build_command,
                             during_test=_default_during_test,
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
    if not build_tree:
        build_tree = ["build"]

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

    build_dir = cont.named_cache_dir("cmake-build", ephemeral=True)
    project_dir = os.getcwd()

    with util.Task("""Cleaning previous build"""):
        _clean_coverage_files(util)

    if not os.environ.get("POLYSQUARE_KEEP_CMAKE_CACHE", None):
        with util.Task("""Restoring cached files to build tree"""):
            _move_directories_ignore_errors(build_tree,
                                            build_dir,
                                            project_dir)

    with _maybe_map_to_drive_letter(project_dir) as mapped_proj_dir:
        after_lint(cont, os_cont, util)

        with configure_context(util) as configure_context_dir:
            with _cmake_generator_context(util,
                                          result.generator) as generator:
                with util.Task("""Configuring {} project""".format(kind)):
                    _configure_cmake_project(cont,
                                             util,
                                             os_cont,
                                             mapped_proj_dir,
                                             project_dir_xform,
                                             build_dir_xform,
                                             build_dir,
                                             configure_context_dir,
                                             configure_cmd,
                                             generator,
                                             result.use_cmake_coverage,
                                             result.cmake_cache_variables)

                with util.Task("""Building {} project""".format(kind)):
                    os_cont.execute(cont,
                                    util.running_output,
                                    *(build_cmd(mapped_proj_dir)))

                with util.Task("""Testing {} project""".format(kind)):
                    if os.path.exists(os.path.join(build_dir,
                                                   "CTestTestfile.cmake")):
                        os_cont.execute(cont,
                                        util.running_output,
                                        *(tuple(list(test_cmd) + [
                                            "--output-on-failure",
                                            "-C",
                                            "Debug"
                                        ])))

                    during_test(cont, os_cont.execute, util, build_dir)

    if not os.environ.get("POLYSQUARE_KEEP_CMAKE_CACHE", None):
        with util.Task("""Moving build tree to cache"""):
            _move_directories_ignore_errors(build_tree,
                                            project_dir,
                                            build_dir)

    after_test(cont, util, build_dir)


NO_CACHE_FILE_PATTERNS = [
    "*/CMakeFiles/*",
    "*/DRIVER.error",
    "*/DRIVER.output",
    "*/Makefile",
    "*/Testing/*",
    "cmake_install.cmake",
    "*.ninja_deps",
    "*.ninja_log",
    "*/rules.ninja",
    "*/build.ninja",
    "CMakeCache.cmake",
    "CTestTestfile.cmake",
    "DartConfiguration.tcl"
]

REMOVE_FILE_PATTERNS = [
    "*/DRIVER.error",
    "*/DRIVER.output",
    "*/Temporary/*"
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
            util.apply_to_files(util.force_remove_tree,
                                build,
                                matching=REMOVE_FILE_PATTERNS)

    check_cmake_like_project(cont,
                             util,
                             shell,
                             kind="cmake",
                             after_test=_after_test,
                             argv=argv)
