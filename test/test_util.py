# /test/test_util.py
#
# Test cases for the bootstrap script.
#
# See /LICENCE.md for Copyright information
"""Test cases for the util script."""

import doctest

import errno

import hashlib

import os

import platform

import stat

import subprocess

import sys

import tempfile

import time

from collections import defaultdict, namedtuple

from test import testutil

from ciscripts.bootstrap import (BashParentEnvironment,
                                 PowershellParentEnvironment,
                                 escaped_printer_with_character)
import ciscripts.util as util

from mock import Mock

from nose_parameterized import param, parameterized

from testtools import ExpectedException, TestCase
from testtools.matchers import (Contains,
                                DocTestMatches,
                                Equals,
                                GreaterThan,
                                MatchesAll,
                                MatchesAny,
                                Not)


class TestPrintMessage(TestCase):
    """Test cases for util.print_message."""

    def test_no_print_to_stdout(self):
        """Test that messages printed to stderr have leading newline."""
        captured_output = testutil.CapturedOutput()
        with captured_output:
            util.print_message("hello")

        self.assertEqual(captured_output.stdout, str())


class OverwrittenEnvironmentVarsTestCase(TestCase):
    """Base class for TestCase where environment variables are overwritten."""

    def __init__(self, *args, **kwargs):
        """Initialize this base class and set instance variables."""
        super(OverwrittenEnvironmentVarsTestCase, self).__init__(*args,
                                                                 **kwargs)
        self._saved_environ = None

    def setUp(self):  # suppress(N802)
        """Set up this test case by saving the current environment."""
        super(OverwrittenEnvironmentVarsTestCase, self).setUp()
        self._saved_environ = os.environ.copy()

    def tearDown(self):  # suppress(N802)
        """Tear down this test case by restoring the saved environment."""
        os.environ = self._saved_environ
        super(OverwrittenEnvironmentVarsTestCase, self).tearDown()


def _get_parent_env_value(config, env_script, var):
    """Evaluate env_script in config.shell and return value of variable."""
    script = (env_script + (" echo \"${%s%s}\"" % (config.var, var))).encode()
    stdout = subprocess.Popen([config.shell, "-"],
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).communicate(script)[0]
    return stdout.strip().decode()


def bash_parent_environment():
    r"""Construct a new BashParentEnvironment printing with \."""
    return BashParentEnvironment(escaped_printer_with_character("\\"))


def powershell_parent_environment():
    r"""Construct a new PowershellParentEnvironment printing with \."""
    return PowershellParentEnvironment(escaped_printer_with_character("`"))


class ParentEnvConfig(namedtuple("ParentEnvConfig",
                                 "parent sep shell env var")):
    """Configuration for testing parent environments."""

    def __repr__(self):
        """Represent as string."""
        return self.shell


class TestOverwriteEnvironmentVariables(OverwrittenEnvironmentVarsTestCase):
    """Test case for util.overwrite_environment_variable."""

    def __init__(self, *args, **kwargs):
        """Initialize instance variables, including parent environment."""
        super(TestOverwriteEnvironmentVariables, self).__init__(*args,
                                                                **kwargs)

    PARENT_ENVIRONMENTS = [
        param(ParentEnvConfig(bash_parent_environment(),
                              ":",
                              "bash",
                              lambda k, v: "export %s=\"%s\";\n" % (k, v),
                              "")),
        param(ParentEnvConfig(powershell_parent_environment(),
                              ";",
                              "powershell",
                              lambda k, v: "$env:%s = \"%s\";\n" % (k, v),
                              "env:"))
    ]

    def _require(self, req):
        """Skip test if req is not available."""
        if util.which(req) is None:
            self.skipTest("""{0} is required to run this test.""".format(req))

    def test_overwritten_environment_variables_in_os_environ(self):
        """Test that overwritten environment variables are in os.environ."""
        with testutil.CapturedOutput():
            util.overwrite_environment_variable(Mock(), "VAR", "VALUE")

        self.assertThat(os.environ, Contains("VAR"))
        self.assertEqual(os.environ["VAR"], "VALUE")

    @parameterized.expand(PARENT_ENVIRONMENTS)
    def test_overwritten_environment_variables_evaluated(self, config):
        """Test that overwritten environment variables are in shell output."""
        captured_output = testutil.CapturedOutput()
        with captured_output:
            util.overwrite_environment_variable(config.parent, "VAR", "VALUE")

        # config.env specifies what we expect the exported variable to
        # look like
        self.assertEqual(captured_output.stdout, config.env("VAR", "VALUE"))

    def test_prepended_environment_variables_in_os_environ_list(self):
        """Prepended environment variables appear in the semicolon list."""
        with testutil.CapturedOutput():
            util.prepend_environment_variable(Mock(), "VAR", "VALUE")
            util.prepend_environment_variable(Mock(),
                                              "VAR",
                                              "SECOND_VALUE")

        self.assertThat(os.environ["VAR"].split(os.pathsep),
                        MatchesAll(Contains("VALUE"),
                                   Contains("SECOND_VALUE")))

    @parameterized.expand(PARENT_ENVIRONMENTS)
    def test_prepended_environment_variables_in_parent(self, config):
        """Prepended variables appear in parent shell environment."""
        self._require(config.shell)

        captured_output = testutil.CapturedOutput()
        with captured_output:
            util.overwrite_environment_variable(config.parent, "VAR", "VALUE")
            util.prepend_environment_variable(config.parent,
                                              "VAR",
                                              "SECOND_VALUE")

        parent_env_value = _get_parent_env_value(config,
                                                 captured_output.stdout,
                                                 "VAR")
        self.assertThat(parent_env_value.split(config.sep),
                        MatchesAll(Contains("VALUE"),
                                   Contains("SECOND_VALUE")))

    def test_unset_environment_variable_in_os_environ(self):
        """Environment overwritten with None unset in os.environ."""
        with testutil.CapturedOutput():
            util.overwrite_environment_variable(Mock(), "VAR", "VALUE")
            util.overwrite_environment_variable(Mock(), "VAR", None)

        self.assertThat(os.environ, Not(Contains("VAR")))

    @parameterized.expand(PARENT_ENVIRONMENTS)
    def test_unset_environment_variable_in_parent(self, config):
        """Environment overwritten with None unset in parent."""
        self._require(config.shell)

        captured_output = testutil.CapturedOutput()
        with captured_output:
            util.overwrite_environment_variable(config.parent, "VAR", "VALUE")
            util.overwrite_environment_variable(config.parent, "VAR", None)

        parent_env_value = _get_parent_env_value(config,
                                                 captured_output.stdout,
                                                 "VAR")
        self.assertEqual(parent_env_value.strip(), "")

    def test_remove_value_from_environment_variable_in_os_environ(self):
        """Remove a value from a colon separated value list in os.environ."""
        with testutil.CapturedOutput():
            util.overwrite_environment_variable(Mock(), "VAR", "VALUE")
            util.prepend_environment_variable(Mock(),
                                              "VAR",
                                              "SECOND_VALUE")
            util.remove_from_environment_variable(Mock(), "VAR", "VALUE")

        self.assertThat(os.environ["VAR"].split(os.pathsep),
                        MatchesAll(Not(Contains("VALUE")),
                                   Contains("SECOND_VALUE")))

    @parameterized.expand(PARENT_ENVIRONMENTS)
    def test_remove_value_from_environment_variable_in_parent(self, config):
        """Remove a value from a colon separated value list in parent shell."""
        self._require(config.shell)

        captured_output = testutil.CapturedOutput()
        with captured_output:
            util.overwrite_environment_variable(config.parent, "VAR", "VALUE")
            util.prepend_environment_variable(config.parent,
                                              "VAR",
                                              "SECOND_VALUE")
            util.remove_from_environment_variable(config.parent,
                                                  "VAR",
                                                  "VALUE")

        parent_env_value = _get_parent_env_value(config,
                                                 captured_output.stdout,
                                                 "VAR")
        self.assertThat(parent_env_value.split(config.sep),
                        MatchesAll(Not(Contains("VALUE")),
                                   Contains("SECOND_VALUE")))


class TestTask(TestCase):
    """Test case for util.Task."""

    def test_description_after_fat_arrow_first_level(self):
        """Description printed after fat arrow on first level."""
        captured_output = testutil.CapturedOutput()
        with captured_output:
            with util.Task("Description"):
                pass

        self.assertEqual(captured_output.stderr, "\n==> Description")

    def test_description_after_dots_second_level(self):
        """Description printed after dots on first level."""
        captured_output = testutil.CapturedOutput()
        with captured_output:
            with util.Task("Description"):
                with util.Task("Secondary Description"):
                    pass

        self.assertEqual("\n==> Description"
                         "\n    ... Secondary Description\n",
                         captured_output.stderr)

    def test_nest_to_third_level(self):
        """Nest to third level with dots."""
        captured_output = testutil.CapturedOutput()
        with captured_output:
            with util.Task("Description"):
                with util.Task("Secondary Description"):
                    with util.Task("Tertiary Description"):
                        pass

        self.assertEqual("\n==> Description"
                         "\n    ... Secondary Description"
                         "\n        ... Tertiary Description\n",
                         captured_output.stderr)

    def output_is_on_level_after_task_description(self):
        """Command output gets printed to level after task description."""
        captured_output = testutil.CapturedOutput()
        with captured_output:
            with util.Task("Description"):
                util.IndentedLogger().message("command_output\n"
                                              "command_output\n")

        self.assertEqual(captured_output.stderr,
                         "\n==> Description"
                         "\n    command_output"
                         "\n    command_output"
                         "\n")


def _utf8_print_cmd():
    """Get a path to a python file which prints a utf-8 check box.

    This is needed because coverage on pypy3 would see the inline
    check box and throw an error, because it doesn't decode it correctly.
    """
    return os.path.join(os.path.realpath(os.path.dirname(__file__)),
                        "utf8_print_cmd.txt")


class TestExecute(TestCase):
    """Test case for util.execute."""

    def test_execute_with_success(self):
        """Execute a command with success."""
        self.assertEqual(0, util.execute(Mock(), util.output_on_fail, "true"))

    def test_execute_with_failure(self):
        """Execute a command with failure."""
        with testutil.CapturedOutput():
            self.assertEqual(1,
                             util.execute(Mock(),
                                          util.output_on_fail,
                                          "false"))

    def test_execute_passes_environment_variables(self):
        """Pass specified environment variables to subprocess."""
        captured_output = testutil.CapturedOutput()
        with captured_output:
            util.execute(Mock(),
                         util.running_output,
                         "python",
                         "-c",
                         "import os; print(os.environ['KEY'])",
                         env={"KEY": "VALUE"})

        self.assertThat(captured_output.stderr,
                        DocTestMatches("...VALUE...",
                                       doctest.ELLIPSIS |
                                       doctest.NORMALIZE_WHITESPACE))

    # suppress(no-self-use)
    def test_instant_failure_calls_through_to_container(self):
        """Execute a command with failure."""
        container = Mock()
        with testutil.CapturedOutput():
            util.execute(container, util.output_on_fail, "false")

        self.assertThat(container.note_failure.call_args_list,
                        Not(Equals(list())))

    def test_execute_with_failure_output(self):
        """Execute a command with failure, showing output."""
        if "POLYSQUARE_ALWAYS_PRINT_PROCESS_OUTPUT" in os.environ:
            del os.environ["POLYSQUARE_ALWAYS_PRINT_PROCESS_OUTPUT"]

        captured_output = testutil.CapturedOutput()
        with captured_output:
            util.execute(Mock(),
                         util.output_on_fail,
                         "python",
                         "/does-not-exist")

        self.assertThat(captured_output.stderr.strip(),
                        Contains("/does-not-exist"))

    def test_override_suppressed_output(self):
        """Override suppressed output with environment variable."""
        os.environ["POLYSQUARE_ALWAYS_PRINT_PROCESS_OUTPUT"] = "1"

        captured_output = testutil.CapturedOutput()
        with captured_output:
            util.execute(Mock(),
                         util.output_on_fail,
                         "python",
                         "-c",
                         "print('Hello')")

        self.assertThat(captured_output.stderr,
                        DocTestMatches("...Hello...",
                                       doctest.ELLIPSIS |
                                       doctest.NORMALIZE_WHITESPACE |
                                       doctest.REPORT_NDIFF))

    def test_execute_with_success_running_output(self):
        """Execute a command with success, but show output."""
        captured_output = testutil.CapturedOutput()
        with captured_output:
            util.execute(Mock(), util.running_output, "python", "--version")

        self.assertThat(captured_output.stderr,
                        DocTestMatches("\nPython ...",
                                       doctest.ELLIPSIS |
                                       doctest.NORMALIZE_WHITESPACE))

    def test_running_output_handles_utf8(self):
        """Handle utf-8 strings correctly in running output."""
        if "POLYSQUARE_ALWAYS_PRINT_PROCESS_OUTPUT" in os.environ:
            del os.environ["POLYSQUARE_ALWAYS_PRINT_PROCESS_OUTPUT"]

        if (platform.python_implementation() != "CPython" or
                platform.system() == "Windows" or
                sys.version_info.major != 3):
            expected = "  ..."
        else:
            expected = u"\N{check mark} ..."

        captured_output = testutil.CapturedOutput()
        with captured_output:
            util.execute(Mock(),
                         util.running_output,
                         "python",
                         _utf8_print_cmd())

        self.assertThat(captured_output.stderr,
                        DocTestMatches(expected,
                                       doctest.ELLIPSIS |
                                       doctest.NORMALIZE_WHITESPACE))

    def test_output_on_fail_handles_utf8(self):
        """Handle utf-8 strings correctly when showing failure output."""
        if "POLYSQUARE_ALWAYS_PRINT_PROCESS_OUTPUT" in os.environ:
            del os.environ["POLYSQUARE_ALWAYS_PRINT_PROCESS_OUTPUT"]

        if (platform.python_implementation() != "CPython" or
                platform.system() == "Windows" or
                sys.version_info.major != 3):
            expected = "  ..."
        else:
            expected = u"\N{check mark} ..."

        captured_output = testutil.CapturedOutput()
        with captured_output:
            util.execute(Mock(),
                         util.running_output,
                         "python",
                         _utf8_print_cmd())

        self.assertThat(captured_output.stderr[1:],
                        DocTestMatches(expected,
                                       doctest.ELLIPSIS |
                                       doctest.NORMALIZE_WHITESPACE))

    def test_running_stderr_at_end(self):
        """Execute a command with success, but display stderr at end."""
        captured_output = testutil.CapturedOutput()
        with captured_output:
            util.execute(Mock(),
                         util.running_output,
                         "python",
                         "-c",
                         "import sys; "
                         "sys.stdout.write('a\\nb'); "
                         "sys.stderr.write('c'); "
                         "sys.stdout.write('d')")

        self.assertEqual(captured_output.stderr.replace("\r\n", "\n"),
                         "\na\nbd\nc\n")

    def test_running_output_no_double_leading_slash_n(self):
        """Using running_output does not allow double-leading slash-n."""
        captured_output = testutil.CapturedOutput()
        with captured_output:
            util.execute(Mock(),
                         util.running_output,
                         "python",
                         "-c",
                         "print(\"\")")

        self.assertThat(captured_output.stderr,
                        DocTestMatches("\n",
                                       doctest.ELLIPSIS |
                                       doctest.NORMALIZE_WHITESPACE))

    def test_execute_show_dots_for_long_running_processes(self):
        """Show dots for long running processes."""
        if "POLYSQUARE_ALWAYS_PRINT_PROCESS_OUTPUT" in os.environ:
            del os.environ["POLYSQUARE_ALWAYS_PRINT_PROCESS_OUTPUT"]

        captured_output = testutil.CapturedOutput()
        with captured_output:
            util.execute(Mock(),
                         util.long_running_suppressed_output(dot_timeout=1),
                         "sleep", "3")

        # There will be fewer dots as the watcher thread start a little
        # later than the subprocess does. However, there can be some cases
        # where there's a little bit of lag between terminating threads, so
        # there might be three dots. Match both cases.
        self.assertThat(captured_output.stderr.strip(),
                        MatchesAny(Equals(".."),  # suppress(PYC90)
                                   Equals("...")))  # suppress(PYC90)


def _full_path_if_exists(path):
    """Return absolute path if it exists, otherwise return basename."""
    if os.path.exists(path):
        return path
    else:
        return os.path.basename(path)


class TestExecutablePaths(OverwrittenEnvironmentVarsTestCase):
    """Test cases for executable path functions (util.which)."""

    def test_raise_executable_not_in_path(self):
        """Raise RuntimeError when executable is not in PATH."""
        temp_dir = tempfile.mkdtemp(prefix=os.path.join(os.getcwd(),
                                                        "executable_path"))
        self.addCleanup(lambda: util.force_remove_tree(temp_dir))
        with tempfile.NamedTemporaryFile(mode="wt",
                                         dir=temp_dir) as temp_file:
            temp_file.write("#!/usr/bin/env python\nprint(\"Test\")")
            os.chmod(temp_file.name, 755)

            with ExpectedException(RuntimeError):
                os.environ["PATH"] = "/does_not_exist"
                util.execute(Mock(),
                             util.long_running_suppressed_output(),
                             os.path.basename(temp_file.name))

    def test_find_executable_file_in_path(self):
        """Find an executable file in the current PATH."""
        with testutil.in_tempdir(os.getcwd(), "executable_path") as temp_dir:
            os.environ["PATH"] = (temp_dir +
                                  os.pathsep +
                                  (os.environ.get("PATH") or ""))

            with tempfile.NamedTemporaryFile(mode="wt",
                                             dir=temp_dir) as temp_file:
                temp_file.write("#!/usr/bin/env python\nprint(\"Test\")")
                os.chmod(temp_file.name,
                         os.stat(temp_file.name).st_mode | stat.S_IRWXU)

                which_result = util.which(os.path.basename(temp_file.name))
                self.assertEqual(temp_file.name.lower(),
                                 which_result.lower())

    def test_find_executable_file_using_pathext(self):
        """Find an executable file using PATHEXT."""
        with testutil.in_tempdir(os.getcwd(), "executable_path") as temp_dir:
            os.environ["PATH"] = (temp_dir +
                                  os.pathsep +
                                  (os.environ.get("PATH") or ""))
            os.environ["PATHEXT"] = ".exe"

            with tempfile.NamedTemporaryFile(mode="wt",
                                             dir=temp_dir,
                                             suffix=".exe") as temp_file:
                temp_file.write("#!/usr/bin/env python\nprint(\"Test\")")
                os.chmod(temp_file.name, 755)

                name = os.path.splitext(os.path.basename(temp_file.name))[0]

                which_result = util.which(name)
                self.assertEqual(temp_file.name.lower(),
                                 which_result.lower())

    def test_process_shebang(self):
        """Explicitly specify interpreter when file has shebang."""
        with testutil.in_tempdir(os.getcwd(), "executable_path") as temp_dir:
            os.environ["PATH"] = (temp_dir +
                                  os.pathsep +
                                  (os.environ.get("PATH") or ""))

            with open(os.path.join(temp_dir, "script"), "wt") as temp_file:
                temp_file.write("#!/usr/bin/env python\nprint(\"Test\")")

            os.chmod(temp_file.name,
                     os.stat(temp_file.name).st_mode | stat.S_IRWXU)

            cmdline = util.process_shebang([temp_file.name])
            self.assertEqual(cmdline,
                             [_full_path_if_exists("/usr/bin/env"),
                              "python",
                              temp_file.name])

    def test_ignore_shebang_when_in_pathext(self):
        """Ignore shebang when extension is in PATHEXT."""
        with testutil.in_tempdir(os.getcwd(), "executable_path") as temp_dir:
            os.environ["PATH"] = (temp_dir +
                                  os.pathsep +
                                  (os.environ.get("PATH") or ""))
            os.environ["PATHEXT"] = ".py"

            with open(os.path.join(temp_dir, "script.py"), "wt") as temp_file:
                temp_file.write("#!/usr/bin/env python\nprint(\"Test\")")

            os.chmod(temp_file.name, 755)

            cmdline = util.process_shebang([temp_file.name])
            self.assertEqual(cmdline, [temp_file.name])

    def test_non_executable_file_not_found(self):
        """Don't find a non executable file in the current PATH."""
        if platform.system() == "Windows":
            self.skipTest("no such thing as execute permission on Windows")

        with testutil.in_tempdir(os.getcwd(), "executable_path") as temp_dir:
            os.environ["PATH"] = (temp_dir + os.pathsep)

            with tempfile.NamedTemporaryFile(mode="wt",
                                             dir=temp_dir) as temp_file:
                temp_file.write("#!/usr/bin/env python\nprint(\"Test\")")

                self.assertEqual(None,
                                 util.which(os.path.basename(temp_file.name)))

    def test_file_not_in_path_not_found(self):
        """Check that executables not in PATH are not found."""
        temp_dir = tempfile.mkdtemp(prefix=os.path.join(os.getcwd(),
                                                        "executable_path"))
        self.addCleanup(lambda: util.force_remove_tree(temp_dir))
        with tempfile.NamedTemporaryFile(mode="wt",
                                         dir=temp_dir) as temp_file:
            temp_file.write("#!/usr/bin/env python\nprint(\"Test\")")
            os.chmod(temp_file.name, 755)

            os.environ["PATH"] = ""

            self.assertEqual(None,
                             util.which(os.path.basename(temp_file.name)))

    def test_symlinks_in_path_get_resolved(self):
        """Returned executable path has symlinks resolved."""
        if platform.system() == "Windows":
            self.skipTest("symlinks not supported on Windows")

        with testutil.in_tempdir(os.getcwd(), "executable_path") as temp_dir:
            link = os.path.join(temp_dir, "link")
            linked = os.path.join(temp_dir, "linked")

            os.mkdir(linked)
            os.symlink(linked, link)

            path_var = (os.environ.get("PATH") or "")

            os.environ["PATH"] = link + os.pathsep + path_var

            with tempfile.NamedTemporaryFile(mode="wt",
                                             dir=linked) as temp_file:
                temp_file.write("#!/usr/bin/env python\nprint(\"Test\")")
                os.chmod(temp_file.name, 755)

                self.assertEqual(temp_file.name,
                                 util.which(os.path.basename(temp_file.name)))

    def test_resolve_relative_paths(self):
        """Resolve relative paths in PATH."""
        with testutil.in_tempdir(os.getcwd(), "executable_path") as temp_dir:
            path_var = (os.environ.get("PATH") or "")
            base = os.path.basename(temp_dir)
            os.environ["PATH"] = "{0}/../{1}{2}{3}".format(temp_dir,
                                                           base,
                                                           os.pathsep,
                                                           path_var)

            with tempfile.NamedTemporaryFile(mode="wt",
                                             dir=temp_dir) as temp_file:
                temp_file.write("#!/usr/bin/env python\nprint(\"Test\")")
                os.chmod(temp_file.name, 755)

                which_result = util.which(os.path.basename(temp_file.name))
                self.assertEqual(temp_file.name.lower(),
                                 which_result.lower())

    # suppress(no-self-use)
    def test_execute_function_if_not_found_by_which(self):
        """Execute function with where_unavailable if executable not found."""
        temp_dir = tempfile.mkdtemp(prefix=os.path.join(os.getcwd(),
                                                        "executable_path"))
        self.addCleanup(lambda: util.force_remove_tree(temp_dir))
        with tempfile.NamedTemporaryFile(mode="wt",
                                         dir=temp_dir) as temp_file:
            temp_file.write("#!/usr/bin/env python\nprint(\"Test\")")
            os.chmod(temp_file.name, 755)

            mock = Mock()
            util.where_unavailable(os.path.basename(temp_file.name),
                                   mock,
                                   "arg")

            mock.assert_called_with("arg")

    # suppress(no-self-use)
    def test_no_execute_function_if_found_by_which(self):
        """where_unavailable doesn't execute function if executable found."""
        with testutil.in_tempdir(os.getcwd(), "executable_path") as temp_dir:
            with tempfile.NamedTemporaryFile(mode="wt",
                                             dir=temp_dir) as temp_file:
                temp_file.write("#!/usr/bin/env python\nprint(\"Test\")")
                os.chmod(temp_file.name, 755)

                with testutil.environment_copy():
                    os.environ["PATH"] = (os.environ["PATH"] +
                                          os.pathsep +
                                          temp_dir)
                    mock = Mock()
                    util.where_unavailable(os.path.basename(temp_file.name),
                                           mock,
                                           "arg")
                    self.assertEquals(mock.call_args_list, list())


class TestApplicationToFilePatterns(TestCase):
    """Test cases for apply_to_files/directories_matching."""

    # suppress(no-self-use)
    def test_apply_to_matching_files_by_prefix(self):
        """Apply functions to files matching prefix."""
        with testutil.in_tempdir(os.getcwd(), "file_patterns") as temp_dir:
            with tempfile.NamedTemporaryFile(mode="wt",
                                             dir=temp_dir) as temp_file:
                temp_file.write("")
                temp_file.flush()

                function_applied = Mock()
                util.apply_to_files(function_applied,
                                    temp_dir,
                                    matching=["{0}/*".format(temp_dir)])

                function_applied.assert_called_with(temp_file.name)

    # suppress(no-self-use)
    def test_apply_to_matching_files_by_suffix(self):
        """Apply functions to files matching suffix."""
        with testutil.in_tempdir(os.getcwd(), "file_patterns") as temp_dir:
            with tempfile.NamedTemporaryFile(mode="wt",
                                             dir=temp_dir,
                                             suffix=".tmp") as temp_file:
                temp_file.write("")
                temp_file.flush()

                function_applied = Mock()
                util.apply_to_files(function_applied,
                                    temp_dir,
                                    matching=["*.tmp"])

                function_applied.assert_called_with(temp_file.name)

    # suppress(no-self-use)
    def test_apply_to_matching_files_by_multiple_suffixes(self):
        """Apply functions to files matching suffix."""
        with testutil.in_tempdir(os.getcwd(), "file_patterns") as temp_dir:
            with tempfile.NamedTemporaryFile(mode="wt",
                                             dir=temp_dir,
                                             suffix=".tmp2") as temp_file:
                temp_file.write("")
                temp_file.flush()

                function_applied = Mock()
                util.apply_to_files(function_applied,
                                    temp_dir,
                                    matching=["*.tmp1",
                                              "*.tmp2"])

                function_applied.assert_called_with(temp_file.name)

    # suppress(no-self-use)
    def test_no_apply_files_not_matching_suffix(self):
        """Don't apply functions to files not matching suffix."""
        with testutil.in_tempdir(os.getcwd(), "file_patterns") as temp_dir:
            with tempfile.NamedTemporaryFile(mode="wt",
                                             dir=temp_dir,
                                             suffix=".tmp") as temp_file:
                temp_file.write("")
                temp_file.flush()

                function_applied = Mock()
                util.apply_to_files(function_applied,
                                    temp_dir,
                                    matching=["*.{0}".format("other")])

                function_applied.assert_not_called()  # suppress(PYC70)

    # suppress(no-self-use)
    def test_apply_to_directories_matching(self):
        """Apply functions to directories matching prefix."""
        with testutil.in_tempdir(os.getcwd(), "file_patterns") as temp_dir:
            with testutil.in_tempdir(os.getcwd(), "matched") as matched:
                base = os.path.basename(matched)
                function_applied = Mock()
                util.apply_to_directories(function_applied,
                                          temp_dir,
                                          matching=["*/{0}".format(base)])

                function_applied.assert_called_with(matched)

    # suppress(no-self-use)
    def test_no_apply_to_directories_not_matching(self):
        """Don't apply to directories."""
        with testutil.in_tempdir(os.getcwd(), "file_patterns") as temp_dir:
            with testutil.in_tempdir(os.getcwd(), "matched"):
                function_applied = Mock()
                util.apply_to_directories(function_applied,
                                          temp_dir,
                                          matching=["{0}/*".format("other")])

                function_applied.assert_not_called()  # suppress(PYC70)


class TestGetSystemIdentifier(TestCase):
    """Test cases for the :get_system_identifier: function."""

    def __init__(self, *args, **kwargs):
        """Initialize this TestCase."""
        super(TestGetSystemIdentifier, self).__init__(*args, **kwargs)
        self.container = None

    def setUp(self):  # suppress(N802)
        """Create a stub class with a temporary directory to store files in."""
        super(TestGetSystemIdentifier, self).setUp()

        def named_cache_dir_func(temp_dir):
            """Return a function to create named cache dirs in temp_dir."""
            def named_cache_dir(self, directory):
                """Create a named cache directory."""
                del self

                cache_dir = os.path.join(temp_dir, directory)
                try:
                    os.makedirs(cache_dir)
                except OSError as error:
                    if error.errno != errno.EEXIST:  # suppress(PYC90)
                        raise error

                return cache_dir

            return named_cache_dir

        temp_dir_prefix = os.path.join(os.getcwd(), "sysid")
        temporary_directory = tempfile.mkdtemp(prefix=temp_dir_prefix)
        self.addCleanup(util.force_remove_tree, temporary_directory)
        cache_dir_func = named_cache_dir_func(temporary_directory)

        self.container = type("StubContainer",
                              (object, ),
                              {"named_cache_dir": cache_dir_func})()

    def test_system_identifier_has_architecture(self):
        """Determined system identifier has architecture."""
        is_64bits = sys.maxsize > 2**32

        if (is_64bits and "64" not in platform.machine() or
                not is_64bits and "64" in platform.machine()):
            self.skipTest("can't reliably get machine ID on mixed binary")

        self.assertThat(util.get_system_identifier(self.container),
                        Contains(platform.machine()))

    def test_system_identifier_has_system_name(self):
        """Determined system identifier has OS name."""
        system_identifier_map = defaultdict(lambda: lambda s: s,
                                            windows=lambda s: "mingw")

        sys_id = platform.system().lower()
        sys_id = system_identifier_map[sys_id](sys_id)
        self.assertThat(util.get_system_identifier(self.container),
                        Contains(sys_id))


class PrepopulatedMTimeContainer(object):  # suppress(too-few-public-methods)
    """Stub for container class, exposes named_cache_dir.

    The current dir will be pre-populated with the md5 of a specified
    filename, with its actual mtime written to it.

    named_cache_dir always returns the current directory.
    """

    def __init__(self, filename):
        """Create cache dir and pre-populate it with mtime file."""
        super(PrepopulatedMTimeContainer, self).__init__()

        if filename:
            filename_stamp = hashlib.md5(filename.encode("utf-8")).hexdigest()
            util.store_current_mtime_in(os.path.join(os.getcwd(),
                                                     filename_stamp))

    def named_cache_dir(self, *args, **kwargs):  # suppress(no-self-use)
        """Return current directory."""
        del args
        del kwargs

        return os.getcwd()


class TestStoredMTimes(TestCase):
    """Test storing and acting on modification times."""

    def test_two_mtimes_have_different_values(self):
        """Two stored modification times have different values."""
        with testutil.in_tempdir(os.getcwd(), "mtimes"):
            util.store_current_mtime_in("1")
            time.sleep(1)
            util.store_current_mtime_in("2")

            self.assertThat(util.fetch_mtime_from("2"),
                            GreaterThan(util.fetch_mtime_from("1")))

    # suppress(no-self-use)
    def test_act_on_no_mtime_file(self):
        """Perform action when modification time file doesn't exist."""
        with testutil.in_tempdir(os.getcwd(), "mtimes"):
            callee = Mock()
            with open("temporary_file", "w") as temporary_file:
                temporary_file.write("contents")
                temporary_file.flush()

            container = PrepopulatedMTimeContainer(temporary_file.name)
            util.where_more_recent(container,
                                   temporary_file.name,
                                   util.fetch_mtime_from("1"),
                                   callee)

            self.assertThat(callee.call_args_list, Not(Equals(list())))

    # suppress(no-self-use)
    def test_no_act_where_file_doesnt_exist(self):
        """Don't perform action when candidate file doesn't exist."""
        with testutil.in_tempdir(os.getcwd(), "mtimes"):
            callee = Mock()
            util.where_more_recent(PrepopulatedMTimeContainer(None),
                                   os.path.join(os.getcwd(), "temp"),
                                   util.fetch_mtime_from("1"),
                                   callee)

            self.assertEqual(callee.call_args_list, list())

    # suppress(no-self-use)
    def test_no_act_where_file_is_up_to_date(self):
        """Don't perform action when candidate file is up to date."""
        with testutil.in_tempdir(os.getcwd(), "mtimes"):
            callee = Mock()
            with open("temporary_file", "w") as temporary_file:
                temporary_file.write("contents")
                temporary_file.flush()

            container = PrepopulatedMTimeContainer(temporary_file.name)

            time.sleep(1)
            util.store_current_mtime_in("1")

            util.where_more_recent(container,
                                   temporary_file.name,
                                   util.fetch_mtime_from("1"),
                                   callee)

            self.assertEqual(callee.call_args_list, list())

    # suppress(no-self-use)
    def test_act_where_file_is_up_to_date(self):
        """Perform action when candidate file is not up to date."""
        with testutil.in_tempdir(os.getcwd(), "mtimes"):
            callee = Mock()

            util.store_current_mtime_in("1")
            time.sleep(1)

            with open("temporary_file", "w") as temporary_file:
                temporary_file.write("contents")
                temporary_file.flush()

            container = PrepopulatedMTimeContainer(temporary_file.name)

            util.where_more_recent(container,
                                   temporary_file.name,
                                   util.fetch_mtime_from("1"),
                                   callee)

            self.assertThat(callee.call_args_list, Not(Equals(list())))
