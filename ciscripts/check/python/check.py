# /ciscripts/check/python/check.py
#
# Run tests and static analysis checks on a python project.
#
# See /LICENCE.md for Copyright information
"""Run tests and static analysis checks on a python project."""

import argparse

import os

from setuptools import find_packages


def run(cont, util, shell, argv=None):
    """Run tests and static analysis checks on this python project.

    This will run the generic project style guide checks on all python files
    and lint all markdown documentation. It then uses /setup.py to run
    the test and lint commands.

    Ideally, the project should have setuptools-green and
    setuptools-prospector-pychecker installed and listed as a dependency
    in its setup_requires.
    """
    parser = argparse.ArgumentParser(description="Run python checks")
    parser.add_argument("--coverage-exclude",
                        nargs="*",
                        type=str,
                        help="Patterns of files to exclude from coverage")
    parser.add_argument("--lint-exclude",
                        nargs="*",
                        type=str,
                        help="Patterns of files to exclude from linting")
    result = parser.parse_args(argv or list())

    config_python = "setup/project/configure_python.py"
    python_ver = os.environ["_POLYSQUARE_PYTHON_VERSION"]
    py_cont = cont.fetch_and_import(config_python).get(cont,
                                                       util,
                                                       shell,
                                                       python_ver)

    with util.Task("""Checking python project style guide compliance"""):
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
        ] + (result.lint_exclude or list())

        cont.fetch_and_import("check/project/lint.py").run(cont,
                                                           util,
                                                           extensions=["py"],
                                                           exclusions=excl,
                                                           block_regexps=supps)

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
        with py_cont.deactivated(util):
            cwd = os.getcwd()
            tests_dir = os.path.join(cwd, "test")
            assert os.path.exists(tests_dir)

            packages = find_packages(exclude=["test"], )
            coverage_exclude = result.coverage_exclude or list()

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
