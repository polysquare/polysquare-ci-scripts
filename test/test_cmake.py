# /test/test_cmake.py
#
# Test cases for a "project" container.
#
# See /LICENCE.md for Copyright information
"""Test cases for a project container."""

import errno

import os

import platform

import shutil

import subprocess

import tempfile

from test import testutil

import ciscripts.bootstrap as bootstrap
import ciscripts.util as util

from nose_parameterized import parameterized

from testtools import TestCase
from testtools.content import text_content
from testtools.matchers import FileExists, Mismatch


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
        if not candidate:
            return Mismatch("""None passed to match""")

        path = self._path
        if os.path.commonprefix([os.path.realpath(path).lower(),
                                 os.path.realpath(candidate).lower()]):
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


def _copytree_ignore_notfound(src, dst):
    """Copy an entire directory tree.

    This is effectively a workaround for situations where shutil.copytree
    is unable to copy some files. Just shell out to rsync, as rsync
    usually always gets it right in complicated cases.

    Where rsync isn't available, then we'll need to fallback to shutil.
    """
    if util.which("rsync"):
        subprocess.check_call(["rsync",
                               "-az",
                               src + os.path.sep,
                               dst + os.path.sep])
    else:
        try:
            shutil.copytree(src, dst)
        except shutil.Error:  # suppress(pointless-except)
            pass

_WHICH_SCRIPT = ("import ciscripts.util;assert ciscripts.util.which('{0}')")


class TestCMakeContainerSetup(TestCase):

    """Test cases for setting up a cmake project container."""

    def __init__(self, *args, **kwargs):
        """Initialize the instance attributes for this test case."""
        super(TestCMakeContainerSetup, self).__init__(*args, **kwargs)
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

        if os.environ.get("CONTAINER_DIR"):
            container_dir = os.environ["CONTAINER_DIR"]
            shutil.rmtree(cls.container_temp_dir)
            _copytree_ignore_notfound(container_dir, cls.container_temp_dir)

            # Delete ciscripts in the copied container
            try:
                shutil.rmtree(os.path.join(cls.container_temp_dir,
                                           "_scripts"))
            except (shutil.Error, OSError):  # suppress(pointless-except)
                pass

        shutil.copytree(os.path.join(parent, "ciscripts"),
                        os.path.join(cls.container_temp_dir,
                                     "_scripts",
                                     "ciscripts"))

        setup_script = "setup/cmake/setup.py"
        cls.setup_container_output = testutil.CapturedOutput()

        extra_args = list()

        # Don't install mdl on AppVeyor - installing any gem is far
        # too slow and will cause the job to time out.
        if os.environ.get("APPVEYOR", None):
            extra_args.append("--no-mdl")

        with cls.setup_container_output:
            printer = bootstrap.escaped_printer_with_character("\\")
            shell = bootstrap.BashParentEnvironment(printer)
            cls.container = bootstrap.ContainerDir(shell,
                                                   cls.container_temp_dir)
            cls.util = cls.container.fetch_and_import("util.py")

            setup_module = cls.container.fetch_and_import(setup_script)
            cls.lang_container = setup_module.run(cls.container,
                                                  util,
                                                  shell,
                                                  extra_args)

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
        super(TestCMakeContainerSetup, self).setUp()
        parent = os.path.realpath(os.path.join(os.path.dirname(__file__),
                                               ".."))
        assert "sample" in os.listdir(parent)
        assert "cmake" in os.listdir(os.path.join(parent, "sample"))

        shutil.copytree(os.path.join(parent, "sample", "cmake"),
                        self.project_dir)
        os.chdir(self.project_dir)

        self.__class__.container.reset_failure_count()

    def tearDown(self):  # suppress(N802)
        """Remove the copy of the sample project."""
        os.chdir(self._directory_on_setup)
        shutil.rmtree(self.project_copy_temp_dir)
        shutil.rmtree(self.__class__.container.named_cache_dir("cmake-build"))

        super(TestCMakeContainerSetup, self).tearDown()

    _PROGRAMS = [
        "polysquare-generic-file-linter",
        "psq-travis-container-exec",
        "psq-travis-container-create"
    ]

    if not os.environ.get("APPVEYOR", None):
        _PROGRAMS.append("mdl")

    @parameterized.expand(_PROGRAMS, testcase_func_doc=format_with_args(0))
    def test_program_is_available_in_python_script(self, program):
        """Executable {0} is available after running setup."""
        self.assertThat(util.which(program),
                        IsInSubdirectoryOf(self.__class__.container_temp_dir))

    @parameterized.expand(_PROGRAMS, testcase_func_doc=format_with_args(0))
    def test_program_is_available_in_parent_shell(self, program):
        """Executable {0} is available in parent shell after running setup."""
        script = _WHICH_SCRIPT.format(program)
        self.assertThat(self.in_parent_context("python -c "
                                               "\"{0}\"".format(script)),
                        SubprocessExitsWith(0))

    _CONTAINERIZED_PROGRAMS = [
        "cmake",
        "ctest"
    ]

    @parameterized.expand(_CONTAINERIZED_PROGRAMS,
                          testcase_func_doc=format_with_args(0))
    def test_containerized_program_is_available(self, program):
        """Executable {0} is available in container after running setup."""
        container = self.__class__.container
        output_strategy = util.output_on_fail
        script = _WHICH_SCRIPT.format(program)
        self.assertEqual(self.__class__.lang_container.execute(container,
                                                               output_strategy,
                                                               "python",
                                                               "-c",
                                                               script,
                                                               program),
                         0)

    def test_run_check_builds_cmake_project_success(self):
        """Running check script builds cmake project."""
        self.assertThat("check/cmake/check.py",
                        CIScriptExitsWith(0,
                                          self.__class__.container,
                                          self.__class__.util,
                                          "--no-mdl"))

    def test_run_check_has_cmake_artifacts(self):
        """After running check, artifacts are present."""
        check_path = "check/cmake/check.py"
        check = self.__class__.container.fetch_and_import(check_path)

        check.run(self.__class__.container,
                  self.__class__.util,
                  None,
                  "--no-mdl")

        build = self.__class__.container.named_cache_dir("cmake-build")
        components = [build]

        # On Windows built binaries go into CMAKE_CFG_INTDIR, which
        # will be Debug in our case.
        if platform.system() == "Windows":
            binary_name = "my_executable.exe"
            components.append("Debug")
        else:
            binary_name = "my_executable"

        components.append(binary_name)
        self.assertThat(os.path.join(*components),
                        FileExists())
