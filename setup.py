# /setup.py
#
# Installation and setup script for polysquare-ci-scripts
#
# See /LICENCE.md for Copyright information
"""Installation and setup script for polysquare-ci-scripts."""

import os
import os.path

import re

import sys

from collections import defaultdict

from contextlib import contextmanager

from distutils.errors import DistutilsArgError

import setuptools

from setuptools import (find_packages, setup)


class GreenTestCommand(setuptools.Command):

    """Provide a test command using green."""

    def run(self):
        """Run tests using green."""
        import green.cmdline
        import green.config

        green.config.sys.argv = ["", "-vvv", "-t"]
        sys.exit(green.cmdline.main())

    def initialize_options(self):  # suppress(unused-function)
        """Set all options to their initial values."""
        pass

    def finalize_options(self):  # suppress(unused-function)
        """Finalize options."""
        pass

    user_options = []  # suppress(unused-variable)
    description = "run tests using the 'green' test runner"
    requirements = [
        "green"
    ]
    dependency_links = []


class CapturedOutput(object):

    """Represents the captured contents of stdout and stderr."""

    def __init__(self):
        """Initialize the class."""
        super(CapturedOutput, self).__init__()
        self.stdout = ""
        self.stderr = ""

        self._stdout_handle = None
        self._stderr_handle = None

    def __enter__(self):
        """Start capturing output."""
        from six.moves import StringIO

        self._stdout_handle = sys.stdout
        self._stderr_handle = sys.stderr

        sys.stdout = StringIO()
        sys.stderr = StringIO()

        return self

    def __exit__(self, type, value, traceback):
        """Finish capturing output."""
        sys.stdout.seek(0)
        self.stdout = sys.stdout.read()

        sys.stderr.seek(0)
        self.stderr = sys.stderr.read()

        sys.stdout = self._stdout_handle
        self._stdout_handle = None

        sys.stderr = self._stderr_handle
        self._stderr_handle = None


class LintCommand(setuptools.Command):

    """Private a lint command."""

    def _parse_suppressions(self, suppressions):
        """Parse a suppressions field and return suppressed codes."""
        return suppressions[len("suppress("):-1].split(",")

    def _suppressed(self, filename, line, code):
        """Return true if linter error code is suppressed inline.

        The suppression format is suppress(CODE1,CODE2,CODE3) etc.
        """
        if not os.path.isfile(os.path.realpath(filename)):
            return False

        if code in self.suppress_codes:
            return True

        try:
            relevant_line = self._file_lines_cache[filename][line - 1]
        except KeyError:
            with open(filename) as f:
                self._file_lines_cache[filename] = f.readlines()

            relevant_line = self._file_lines_cache[filename][line - 1]

        above_line = self._file_lines_cache[filename][line - 2]

        try:
            suppressions_function = relevant_line.split("#")[1].strip()
            if suppressions_function.startswith("suppress("):
                return code in self._parse_suppressions(suppressions_function)
        except IndexError:
            suppressions_function = above_line.strip()[1:].strip()
            if suppressions_function.startswith("suppress("):
                return code in self._parse_suppressions(suppressions_function)
        finally:
            pass

    @contextmanager
    def _custom_argv(self, argv):
        """Overwrite argv[1:] with argv, restore on exit."""
        backup_argv = sys.argv
        sys.argv = backup_argv[:1] + argv
        yield
        sys.argv = backup_argv

    def _get_files_to_lint(self, external_directories):
        """Get files to lint."""
        import os
        from fnmatch import filter as fnfilter
        from fnmatch import fnmatch

        def is_excluded(filename, exclusions):
            """True if filename matches any of exclusions."""
            for exclusion in exclusions:
                if fnmatch(filename, exclusion):
                    return True

            return False

        all_f = []

        for external_dir in external_directories:
            for r, dirs, files in os.walk(external_dir):
                all_f.extend(fnfilter([os.path.join(r, f) for f in files],
                                      "*.py"))

        for package in (self.distribution.packages or list()):
            for r, dirs, files in os.walk(package):
                all_f.extend(fnfilter([os.path.join(r, f) for f in files],
                                      "*.py"))

        for filename in (self.distribution.py_modules or list()):
            all_f.append(os.path.realpath(filename + ".py"))

        all_f.append(os.path.join(os.getcwd(), "setup.py"))

        exclusions = [
            "*.egg/*",
            "*.eggs/*"
        ] + self.exclusions
        return [f for f in all_f if not is_excluded(f, exclusions)]

    def _patch_pep257(self):
        """Monkey-patch pep257 after imports to avoid info logging."""
        import pep257

        def dummy(*args, **kwargs):
            """A dummy logging function."""
            pass

        pep257.log.info = dummy  # suppress(unused-attribute)

    def _run_flake8_checks(self, m_dict, files_to_lint):
        """Run flake8 checks and stores results in m_dict."""
        from flake8.engine import get_style_guide
        from pep8 import BaseReport
        from prospector.message import Message, Location

        self._patch_pep257()

        cwd = os.getcwd()

        class Flake8MergeReporter(BaseReport):

            """An implementation of pep8.BaseReport merging results.

            This implementation merges results from the flake8 report
            into the prospector report created earlier.
            """

            def __init__(self, options):
                """Initialize this Flake8MergeReporter."""
                super(Flake8MergeReporter, self).__init__(options)
                self._current_file = ""

            def init_file(self, filename, lines, expected, line_offset):
                """Start processing filename."""
                self._current_file = os.path.realpath(os.path.join(cwd,
                                                                   filename))

                super(Flake8MergeReporter, self).init_file(filename,
                                                           lines,
                                                           expected,
                                                           line_offset)

            def error(self, line, offset, text, check):
                """Record error and merge with m_dict."""
                code = super(Flake8MergeReporter, self).error(line,
                                                              offset,
                                                              text,
                                                              check)

                fn = self._current_file
                if not isinstance(m_dict[fn][line][code], Message):
                    m_dict[fn][line][code] = Message(code,
                                                     code,
                                                     Location(fn,
                                                              None,
                                                              None,
                                                              line,
                                                              offset),
                                                     text[5:])

        get_style_guide(reporter=Flake8MergeReporter,
                        jobs="1").check_files(paths=files_to_lint)

    def _run_prospector_checks(self, m_dict, all_files):
        """Run prospector checks, storing results in m_dict."""
        from prospector.run import Prospector, ProspectorConfig

        self._patch_pep257()
        cwd = os.getcwd()

        prospector_argv = [
            "-F",
            "-D",
            "-M"
        ]

        def run_prospector_on(files_to_lint, tools):
            """Run prospector on files_to_lint, using the specified tools.

            This function enables us to run different tools on different
            classes of files, which is necessary in the case of tests.
            """
            if len(tools) > 0:
                tools_argv = ("-t " + " -t ".join(tools)).split(" ")
            else:
                tools_argv = []

            all_argv = prospector_argv + tools_argv + files_to_lint
            with self._custom_argv(all_argv):
                prospector = Prospector(ProspectorConfig())
                prospector.execute()
                for m in (prospector.get_messages() or list()):
                    m.to_absolute_path(cwd)
                    loc = m.location

                    if isinstance(m_dict[loc.path][loc.line][m.code],
                                  defaultdict):
                        m_dict[loc.path][loc.line][m.code] = m

        is_test = re.compile(r"^.*test[^{0}]*.py$".format(os.path.sep))

        run_prospector_on(all_files, ["dodgy", "pep257", "pep8", "pyflakes"])
        run_prospector_on([f for f in all_files if not is_test.match(f)],
                          ["frosted", "vulture"])

    def _run_pychecker_checks(self, m_dict, files_to_lint):
        """Run pychecker checks, storing results in m_dict."""
        os.environ["PYCHECKER_DISABLED"] = "True"

        from pychecker import checker
        from pychecker import pcmodules as pcm
        from pychecker import warn
        from pychecker import Config
        from prospector.message import Message, Location

        files = files_to_lint
        setup_py_file = os.path.realpath(os.path.join(os.getcwd(), "setup.py"))
        files = [f for f in files if os.path.realpath(f) != setup_py_file]
        args = ["--only",
                "--limit",
                "1000",
                "-Q",
                "-8",
                "-2",
                "-1",
                "-a",
                "--changetypes",
                "--no-unreachable",
                "-v"]
        config, files, supps = Config.setupFromArgs(args + files)

        with self._custom_argv([]):
            with CapturedOutput():
                checker.processFiles(files, config, supps)
                check_modules = [m for m in pcm.getPCModules() if m.check]
                warnings = warn.find(check_modules, config, supps)

        for warning in warnings:
            code = "PYC" + str(warning.level)
            path = warning.file
            line = warning.line
            if isinstance(m_dict[path][line][code],
                          defaultdict):
                m_dict[path][line][code] = Message(code,
                                                   code,
                                                   Location(path,
                                                            None,
                                                            None,
                                                            line,
                                                            0),
                                                   str(warning.err))

    def _run_pyroma_checks(self, m_dict):
        """Run pyroma on the /setup.py file."""
        from pyroma import projectdata, ratings
        from prospector.message import Message, Location

        data = projectdata.get_data(os.getcwd())
        all_tests = ratings.ALL_TESTS
        for test in [mod() for mod in [t.__class__ for t in all_tests]]:
            if test.test(data) == False:
                class_name = test.__class__.__name__
                if isinstance(m_dict["setup.py"][0][class_name],
                              defaultdict):
                    loc = Location("setup.py", None, None, 0, 0)
                    msg = test.message()
                    m_dict["setup.py"][0][class_name] = Message("pyroma",
                                                                class_name,
                                                                loc,
                                                                msg)

    def run(self):
        """Run linters."""
        from prospector.formatters.pylint import PylintFormatter

        def make_default_dict():
            """Callable to always return a defaultdict."""
            def constructor():
                """Make a defaultdict from make_default_dict."""
                return defaultdict(make_default_dict())

            return constructor

        m_dict = defaultdict(make_default_dict())

        cwd = os.getcwd()
        files_to_lint = self._get_files_to_lint([os.path.join(cwd, "test")])

        self._run_prospector_checks(m_dict, files_to_lint)
        self._run_flake8_checks(m_dict, files_to_lint)
        self._run_pychecker_checks(m_dict, files_to_lint)
        self._run_pyroma_checks(m_dict)

        messages = []
        for filename in m_dict.values():
            for line in filename.values():
                for message in line.values():
                    if not self._suppressed(message.location.path,
                                            message.location.line,
                                            message.code):
                        message.to_relative_path(cwd)
                        messages.append(message)

        sys.stdout.write(PylintFormatter(dict(),
                                         messages,
                                         None).render(messages=True,
                                                      summary=False,
                                                      profile=False) + "\n")

        if len(messages):
            sys.exit(1)

    def initialize_options(self):
        """Set all options to their initial values."""
        self._file_lines_cache = dict()
        self.suppress_codes = []
        self.exclusions = []

    def finalize_options(self):
        """Finalize all options."""
        for option in ["suppress-codes", "exclusions"]:
            attribute = option.replace("-", "_")
            if isinstance(getattr(self, attribute), str):
                setattr(self, attribute, getattr(self, attribute).split(","))

            if not isinstance(getattr(self, attribute), list):
                raise DistutilsArgError("--{0} must be a list".format(option))

    user_options = [
        ("suppress-codes=", None, "Error codes to suppress"),
        ("exclusions=", None, "Glob expressions of files to exclude")
    ]
    description = "run linter checks using prospector, flake8 and pychecker"
    requirements = [
        "pep8",
        "pylint",
        "pylint-common",
        "dodgy",
        "frosted",
        "mccabe",
        "pep257",
        "pyflakes",
        "pyroma",
        "vulture",
        "prospector",
        "flake8==2.3.0",
        "flake8-blind-except",
        "flake8-docstrings",
        "flake8-double-quotes",
        "flake8-import-order",
        "flake8-todo",
        "pychecker",
        "six"
    ]
    dependency_links = [
        ("https://github.com/landscapeio/prospector/tarball/master"
         "#egg=prospector"),
        ("http://downloads.sourceforge.net/project/pychecker/pychecker/0.8.19/"
         "pychecker-0.8.19.tar.gz#egg=pychecker-0.8.19")
    ]

setup(name="polysquare-ci-scripts",
      version="0.0.6",
      description="Polysquare Continuous Integration Scripts",
      long_description_markdown_filename="README.md",
      author="Sam Spilsbury",
      author_email="smspillaz@gmail.com",
      url="http://github.com/polysquare/polysquare-ci-scripts",
      classifiers=["Development Status :: 3 - Alpha",
                   "Programming Language :: Python :: 2",
                   "Programming Language :: Python :: 2.7",
                   "Programming Language :: Python :: 3",
                   "Programming Language :: Python :: 3.1",
                   "Programming Language :: Python :: 3.2",
                   "Programming Language :: Python :: 3.3",
                   "Programming Language :: Python :: 3.4",
                   "Intended Audience :: Developers",
                   "Topic :: Software Development :: Build Tools",
                   "License :: OSI Approved :: MIT License"],
      license="MIT",
      keywords="development linters",
      packages=find_packages(exclude=["test"]),
      setup_requires=["setuptools-markdown"],
      cmdclass={
          "test": GreenTestCommand,
          "lint": LintCommand
      },
      extras_require={
          "test": [
              "nose",
              "nose-parameterized<=0.4.0",
              "testtools"
          ] + GreenTestCommand.requirements,
          "lint": LintCommand.requirements
      },
      dependency_links=[
          ("https://github.com/smspillaz/nose-parameterized/tarball/"
           "detailed-docs#egg=nose-parameterized-0.4.0"),
      ] + LintCommand.dependency_links,
      zip_safe=True,
      include_package_data=True)
