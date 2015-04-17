# /test/test_project.py
#
# Test cases for a "project" container.
#
# See /LICENCE.md for Copyright information
"""Test cases for a project container."""

import errno

import os

import shutil

import subprocess

import tempfile

from test import testutil

import ciscripts.bootstrap as bootstrap
import ciscripts.util as util

from nose_parameterized import parameterized

from testtools import TestCase
from testtools.content import text_content
from testtools.matchers import Mismatch


class IsInSubdirectoryOf(object):  # suppress(too-few-public-methods)

    """Match if a path is a subdirectory of the specified path."""

    def __init__(self, path):
        """Initialize mather for this path."""
        super(IsInSubdirectoryOf, self).__init__()
        self._path = path

    def __str__(self):
        """Represent matcher as string."""
        return "IsInSubdirectoryOf({0})".format(repr(self._path))

    def match(self, candidate):
        """Return Mismatch if candidate is not in a subdirectory of path."""
        path = self._path
        if os.path.commonprefix([os.path.realpath(path),
                                 os.path.realpath(candidate)]):
            return None
        else:
            return Mismatch("{0} is not in a subdir of {1}".format(candidate,
                                                                   path))


class SubprocessExitWithMismatch(object):

    """Detail of a SubprocessExitsWith mismatch."""

    # suppress(too-many-arguments)
    def __init__(self, popen_command, code, expected, stdout, stderr):
        """Initialize this mismatch detail object."""
        super(SubprocessExitWithMismatch, self).__init__()

        command = " ".join(popen_command)
        self._msg = "{0} exited with {1}, but expected {2}".format(command,
                                                                   code,
                                                                   expected)
        self._details = {
            "Output": text_content(stdout),
            "Errors": text_content(stderr)
        }

    def describe(self):
        """Return message."""
        return self._msg

    def get_details(self):
        """Return details."""
        return self._details


class SubprocessExitsWith(object):  # suppress(too-few-public-methods)

    """Match if the subprocess to be executed exits with the expected code."""

    def __init__(self, expected_code):
        """Initialize matcher for this expected code."""
        super(SubprocessExitsWith, self).__init__()
        self._expected_code = expected_code

    def __str__(self):
        """Convert matcher to string."""
        return "SubprocessExitsWith({0})".format(self._expected_code)

    def match(self, subprocess_args):
        """Fail if subprocess exits with unexpected code."""
        process = subprocess.Popen(subprocess_args,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

        code = process.wait()
        if code != self._expected_code:
            return SubprocessExitWithMismatch(subprocess_args,
                                              code,
                                              self._expected_code,
                                              process.stdout.read(),
                                              process.stderr.read())


class CIScriptExitsWith(object):  # suppress(too-few-public-methods)

    """Match if the specified ci-script runs with its arguments."""

    def __init__(self, expected_status, container, util_mod, *args, **kwargs):
        """Initialize matcher with the arguments we run the script with."""
        super(CIScriptExitsWith, self).__init__()
        self._expected_status = expected_status
        self._args = args
        self._kwargs = kwargs
        self._container = container
        self._util = util_mod

    def __str__(self):
        """Represent this matcher as a string."""
        return "CIScriptExitsWith({0})".format(", ".join(self._args))

    def match(self, script):
        """Match if this script runs successfully."""
        captured_output = testutil.CapturedOutput()
        with captured_output:
            run_args = [self._container, self._util] + list(self._args)
            run_kwargs = self._kwargs
            self._container.fetch_and_import(script).run(*run_args,
                                                         **run_kwargs)

        result = self._container.return_code()
        if result != self._expected_status:
            return SubprocessExitWithMismatch(["python", script] +
                                              list(self._args),
                                              result,
                                              self._expected_status,
                                              captured_output.stdout,
                                              captured_output.stderr)


def format_with_args(*args):
    """Return a function that formats a docstring."""
    def formatter(func, _, params):
        """Return formatted docstring with argument numbers in args."""
        pa = params.args
        format_args = [pa[i] for i in range(0, len(pa)) if i in args]

        return func.__doc__.format(*format_args)

    return formatter

LICENCE_STRING = "See /LICENCE.md for Copyright information"


def write_valid_header(f):
    """Write a valid header to file."""
    file_path = os.path.abspath(f.name)
    common_prefix = os.path.commonprefix([file_path, os.getcwd()])
    f.write("#!/bin/bash\n"
            "# {path}\n"
            "#\n"
            "# Description\n"
            "#\n"
            "# {licence}\n\n".format(path=file_path[len(common_prefix):],
                                     licence=LICENCE_STRING))
    f.flush()


def write_invalid_header(f):
    """Write a invalid header to file."""
    file_path = os.path.abspath(f.name)
    common_prefix = os.path.commonprefix([file_path, os.getcwd()])
    f.write("#!/bin/bash\n"
            "# error-{path}\n"
            "#\n"
            "# Description\n"
            "#\n"
            "# {licence}\n".format(path=file_path[len(common_prefix):],
                                   licence=LICENCE_STRING))
    f.flush()


class TestProjectContainerSetup(TestCase):

    """Test cases for setting up a project container."""

    def __init__(self, *args, **kwargs):
        """Initialize the instance attributes for this test case."""
        super(TestProjectContainerSetup, self).__init__(*args, **kwargs)
        self.project_copy_temp_dir = tempfile.mkdtemp(dir=os.getcwd())
        self.project_dir = os.path.join(self.project_copy_temp_dir, "project")
        self._directory_on_setup = os.getcwd()

    def in_parent_context(self, command):
        """Get script to run command in parent context.

        The 'parent context' in this case is a shell script where the
        standard output of the container's setup script has been evaluated,
        eg, all environment variables are exported.
        """
        script = "{0}{1}".format(self.__class__.setup_container_output.stdout,
                                 command)
        return ["bash", "-c", script]

    @classmethod
    def setUpClass(cls):  # suppress(N802)
        """Call container setup script."""
        parent = os.path.realpath(os.path.join(os.path.dirname(__file__),
                                               ".."))
        assert "ciscripts" in os.listdir(parent)

        cls.container_temp_dir = tempfile.mkdtemp(dir=os.getcwd())
        shutil.copytree(os.path.join(parent, "ciscripts"),
                        os.path.join(cls.container_temp_dir,
                                     "_scripts",
                                     "ciscripts"))
        if os.environ.get("CONTAINER_DIR"):
            shutil.copytree(os.path.join(os.environ["CONTAINER_DIR"],
                                         "_cache"),
                            os.path.join(cls.container_temp_dir, "_cache"))
            shutil.copytree(os.path.join(os.environ["CONTAINER_DIR"],
                                         "_languages"),
                            os.path.join(cls.container_temp_dir,
                                         "_languages"))
        setup_script = "setup/project/setup.py"
        cls.setup_container_output = testutil.CapturedOutput()

        with cls.setup_container_output:
            shell = bootstrap.BashParentEnvironment(bootstrap.escaped_printer)
            cls.container = bootstrap.ContainerDir(shell,
                                                   cls.container_temp_dir)
            cls.util = cls.container.fetch_and_import("util.py")
            cls.container.fetch_and_import(setup_script).run(cls.container,
                                                             util,
                                                             shell)

        assert cls.container.return_code() == 0

    @classmethod
    def tearDownClass(cls):  # suppress(N802)
        """Remove container."""
        try:
            shutil.rmtree(cls.container_temp_dir)
        except OSError as err:
            if err.errno != errno.ENOENT:  # suppress(PYC90)
                raise err

    def setUp(self):  # suppress(N802)
        """Create a copy of and enter sample project directory."""
        super(TestProjectContainerSetup, self).setUp()
        parent = os.path.realpath(os.path.join(os.path.dirname(__file__),
                                               ".."))
        assert "sample" in os.listdir(parent)
        assert "project" in os.listdir(os.path.join(parent, "sample"))

        shutil.copytree(os.path.join(parent, "sample", "project"),
                        self.project_dir)
        os.chdir(self.project_dir)

        self.__class__.container.reset_failure_count()

    def tearDown(self):  # suppress(N802)
        """Remove the copy of the sample project."""
        os.chdir(self._directory_on_setup)
        shutil.rmtree(self.project_copy_temp_dir)

        super(TestProjectContainerSetup, self).tearDown()

    _PROGRAMS = ["polysquare-generic-file-linter", "mdl"]

    @parameterized.expand(_PROGRAMS, testcase_func_doc=format_with_args(0))
    def test_program_is_available_in_python_script(self, program):
        """Executable {0} is available after running setup."""
        self.assertThat(util.which(program),
                        IsInSubdirectoryOf(self.__class__.container_temp_dir))

    @parameterized.expand(_PROGRAMS, testcase_func_doc=format_with_args(0))
    def test_program_is_available_in_parent_shell(self, program):
        """Executable {0} is available in parent shell after running setup."""
        self.assertThat(self.in_parent_context("which {0}".format(program)),
                        SubprocessExitsWith(0))

    def test_lint_with_style_guide_linter_success(self):
        """Success code if all files satisfy style guide linter."""
        with tempfile.NamedTemporaryFile(mode="wt",
                                         dir=os.getcwd(),
                                         suffix=".sh") as f:
            write_valid_header(f)

            self.assertThat("check/project/lint.py",
                            CIScriptExitsWith(0,
                                              self.__class__.container,
                                              self.__class__.util,
                                              extensions=["sh"]))

    def test_lint_with_style_guide_linter_failure(self):
        """Failure code if one file doesn't satisfy style guide linter."""
        with tempfile.NamedTemporaryFile(mode="wt",
                                         dir=os.getcwd(),
                                         suffix=".sh") as f:
            write_invalid_header(f)
            container = self.__class__.container

            self.assertThat("check/project/lint.py",
                            CIScriptExitsWith(1,
                                              container,
                                              self.__class__.util,
                                              extensions=["sh"]))

    def test_lint_files_in_multiple_subdirectories(self):
        """Style guide linter runs over multiple subdirectories."""
        success_dir = tempfile.mkdtemp(dir=os.getcwd())
        success_file = tempfile.NamedTemporaryFile(mode="wt",
                                                   dir=success_dir,
                                                   suffix=".sh")

        failure_dir = tempfile.mkdtemp(dir=os.getcwd())
        failure_file = tempfile.NamedTemporaryFile(mode="wt",
                                                   dir=failure_dir,
                                                   suffix=".sh")

        write_valid_header(success_file)
        write_invalid_header(failure_file)

        self.assertThat("check/project/lint.py",
                        CIScriptExitsWith(1,
                                          self.__class__.container,
                                          self.__class__.util,
                                          extensions=["sh"],
                                          directories=[success_dir,
                                                       failure_dir]))

    def test_lint_files_with_multiple_extensions(self):
        """Style guide linter runs over multiple extensions."""
        cwd = os.getcwd()
        success_file = tempfile.NamedTemporaryFile(mode="wt",
                                                   dir=cwd,
                                                   suffix=".zh")
        failure_file = tempfile.NamedTemporaryFile(mode="wt",
                                                   dir=cwd,
                                                   suffix=".sh")

        write_valid_header(success_file)
        write_invalid_header(failure_file)

        self.assertThat("check/project/lint.py",
                        CIScriptExitsWith(1,
                                          self.__class__.container,
                                          self.__class__.util,
                                          extensions=["sh"]))

    def test_files_can_be_excluded_from_linting(self):
        """Exclude certain files from style guide linter."""
        cwd = os.getcwd()
        success_file = tempfile.NamedTemporaryFile(mode="wt",
                                                   dir=cwd,
                                                   suffix=".sh")
        failure_file = tempfile.NamedTemporaryFile(mode="wt",
                                                   dir=cwd,
                                                   suffix=".zh")

        write_valid_header(success_file)
        write_invalid_header(failure_file)

        fail_path = os.path.realpath(failure_file.name)

        self.assertThat("check/project/lint.py",
                        CIScriptExitsWith(0,
                                          self.__class__.container,
                                          self.__class__.util,
                                          extensions=["sh"],
                                          exclusions=[fail_path]))

    def test_many_files_can_be_excluded_from_linting(self):
        """Exclude many files from style guide linting."""
        cwd = os.getcwd()
        success_file = tempfile.NamedTemporaryFile(mode="wt",
                                                   dir=cwd,
                                                   suffix=".sh")
        failure_file = tempfile.NamedTemporaryFile(mode="wt",
                                                   dir=cwd,
                                                   suffix=".zh")
        second_failure_file = tempfile.NamedTemporaryFile(mode="wt",
                                                          dir=cwd,
                                                          suffix=".zh")

        write_valid_header(success_file)
        write_invalid_header(failure_file)
        write_invalid_header(second_failure_file)

        fail_path = os.path.realpath(failure_file.name)
        second_fail_path = os.path.realpath(second_failure_file.name)

        self.assertThat("check/project/lint.py",
                        CIScriptExitsWith(0,
                                          self.__class__.container,
                                          self.__class__.util,
                                          extensions=["sh"],
                                          exclusions=[
                                              fail_path,
                                              second_fail_path
                                          ]))

    def test_linting_of_markdown_documentation_with_success(self):
        """Lint markdown documentation with success exit code."""
        with tempfile.NamedTemporaryFile(dir=os.getcwd(), suffix=".md"):
            self.assertThat("check/project/lint.py",
                            CIScriptExitsWith(0,
                                              self.__class__.container,
                                              self.__class__.util,
                                              extensions=["other"]))

    def test_linting_of_markdown_documentation_with_failure(self):
        """Lint markdown documentation with success exit code."""
        with tempfile.NamedTemporaryFile(mode="wt",
                                         dir=os.getcwd(),
                                         suffix=".md") as f:
            f.write("Level One\n==\n\n## Level Two ##\n")
            f.flush()

            self.assertThat("check/project/lint.py",
                            CIScriptExitsWith(1,
                                              self.__class__.container,
                                              self.__class__.util,
                                              extensions=["other"]))
