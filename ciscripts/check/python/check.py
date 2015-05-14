# /ciscripts/check/python/check.py
#
# Run tests and static analysis checks on a python project.
#
# See /LICENCE.md for Copyright information
"""Run tests and static analysis checks on a python project."""

import argparse

import os

import subprocess

from collections import defaultdict

from setuptools import find_packages


def _run_style_guide_lint(cont, util, lint_exclude, no_mdl):
    """Run /ciscripts/check/project/lint.py on this python project."""
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
    ] + lint_exclude

    cont.fetch_and_import("check/project/lint.py").run(cont,
                                                       util,
                                                       no_mdl,
                                                       extensions=["py"],
                                                       exclusions=excl,
                                                       block_regexps=supps)


def _run_tests_and_coverage(cont, py_cont, util, coverage_exclude):
    """Run /setup.py green on this python project."""
    with py_cont.deactivated(util):
        cwd = os.getcwd()
        tests_dir = os.path.join(cwd, "test")
        assert os.path.exists(tests_dir)

        packages = find_packages(exclude=["test"], )

        with util.in_dir(tests_dir):
            util.execute(cont,
                         util.running_output,
                         "coverage",
                         "run",
                         "--source=" + ",".join(packages),
                         "--omit=" + ",".join(coverage_exclude),
                         os.path.join(cwd, "setup.py"),
                         "green")

            util.execute(cont, util.running_output, "coverage", "report")


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

    config_python = "setup/project/configure_python.py"
    python_ver = defaultdict(lambda: os.environ["_POLYSQUARE_PYTHON_VERSION"])
    py_cont = cont.fetch_and_import(config_python).get(cont,
                                                       util,
                                                       shell,
                                                       python_ver)

    with util.Task("""Checking python project style guide compliance"""):
        _run_style_guide_lint(cont,
                              util,
                              result.lint_exclude or list(),
                              result.no_mdl)

    with util.Task("""Creating development installation"""):
        util.execute(cont,
                     util.output_on_fail,
                     "python",
                     "setup.py",
                     "develop")

    with util.Task("""Linting python project"""):
        util.execute(cont,
                     util.output_on_fail,
                     "python",
                     "setup.py",
                     "polysquarelint",
                     "--suppress-codes=LongDescription,TestSuite")

    with util.Task("""Running python project tests"""):
        _run_tests_and_coverage(cont,
                                py_cont,
                                util,
                                result.coverage_exclude or list())

    with util.Task("""Uninstalling development installation"""):
        pkg, _ = subprocess.Popen(["python", "setup.py", "--name"],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE).communicate()
        util.execute(cont, util.output_on_fail, "pip", "uninstall", "-y", pkg)
