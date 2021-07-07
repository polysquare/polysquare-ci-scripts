# /ciscripts/check/python/check.py
#
# Run tests and static analysis checks on a python project.
#
# See /LICENCE.md for Copyright information
"""Run tests and static analysis checks on a python project."""

import argparse

import os

import shutil


def style_guide_exclusions(lint_exclude):
    """Return a tuple of (suppressions, exclusions).

    suppressions refers to patterns in source code that shouldn't trigger
    any warnings from polysquare-generic-file-linter.

    exclusions refers to directories in a python project that should
    be excluded from all linting.
    """
    supps = [
        r"\bpylint:disable=[^\s]*\b",
        r"\bNOLINT:[^\s]*\b",
        r"\bNOQA[^\s]*\b"
    ]
    excl = [
        os.path.join(os.getcwd(), ".eggs", "*"),
        os.path.join(os.getcwd(), "*.egg", "*"),
        os.path.join(os.getcwd(), "*", "build", "*"),
        os.path.join(os.getcwd(), "build", "*"),
        os.path.join(os.getcwd(), "*", "dist", "*"),
        os.path.join(os.getcwd(), "dist", "*"),
        os.path.join(os.getcwd(), "*", "*.egg-info", "*"),
        os.path.join(os.getcwd(), "*.egg-info", "*")
    ] + (lint_exclude or list())

    return (supps, excl)


def _run_style_guide_lint(cont, util, lint_exclude, no_mdl):
    """Run /ciscripts/check/project/lint.py on this python project."""
    supps, excl = style_guide_exclusions(lint_exclude)

    cont.fetch_and_import("check/project/lint.py").run(cont,
                                                       util,
                                                       None,
                                                       None,
                                                       no_mdl=no_mdl,
                                                       extensions=["py"],
                                                       exclusions=excl,
                                                       block_regexps=supps)


def _run_tests_and_coverage(cont, util, coverage_exclude):
    """Run /setup.py green on this python project."""
    assert os.path.exists(os.path.join(os.getcwd(), "test"))

    util.execute(cont,
                 util.running_output,
                 "python",
                 "setup.py",
                 "green",
                 "--coverage",
                 "--coverage-omit=" + ",".join(coverage_exclude),
                 "--target=test")


def lint_python(cont, util, shell, lint_exclude=None):
    """Run python-specific lint checks on this project."""
    config_python = "setup/project/configure_python.py"
    py_ver = util.language_version("python3")
    py_cont = cont.fetch_and_import(config_python).get(cont,
                                                       util,
                                                       shell,
                                                       py_ver)
    lint_exclude = (lint_exclude or []) + ["*/container/*"]

    with util.Task("""Linting python project"""):
        with py_cont.activated(util):
            suppress = [
                "wrong-import-order",
                "LongDescription",
                "TestSuite",
                "D203",
                "D213",
                "I102",
                "I202"
            ]
            util.execute(cont,
                         util.long_running_suppressed_output(),
                         "python",
                         "setup.py",
                         "polysquarelint",
                         "--exclusions=" + ",".join(lint_exclude),
                         "--suppress-codes=" + ",".join(suppress),
                         ("--stamp-directory=" +
                          cont.named_cache_dir("polysquarelint-stamp",
                                               ephemeral=False)))


def run(cont, util, shell, argv=None):
    """Run tests and static analysis checks on this python project.

    This will run the generic project style guide checks on all python files
    and lint all markdown documentation. It then uses /setup.py to run
    the test and lint commands.

    Ideally, the project should have setuptools-green and
    setuptools-prospector-pychecker installed and listed as a dependency
    in its setup_requires.
    """
    parser = argparse.ArgumentParser(description="""Run python checks""")
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
    result = parser.parse_args(argv or list())

    with util.Task("""Checking python project style guide compliance"""):
        _run_style_guide_lint(cont,
                              util,
                              result.lint_exclude or list(),
                              result.no_mdl)

    install_log = os.path.join(cont.named_cache_dir("python-install"), "log")

    lint_python(cont, util, shell, lint_exclude=result.lint_exclude)

    with util.Task("""Creating development installation """):
        util.execute(cont,
                     util.output_on_fail,
                     "python",
                     "setup.py",
                     "install",
                     "--record",
                     install_log)

    if os.path.exists(os.path.join(os.getcwd(), "test")):
        with util.Task("""Running python project tests"""):
            _run_tests_and_coverage(cont,
                                    util,
                                    result.coverage_exclude or list())

    with util.Task("""Uninstalling development installation"""):
        with open(install_log) as install_log_file:
            for filename in install_log_file.readlines():
                try:
                    if os.path.isdir(filename):
                        util.force_remove_tree(filename)
                    else:
                        os.remove(filename)
                # suppress(pointless-except)
                except (OSError, shutil.Error):
                    pass
