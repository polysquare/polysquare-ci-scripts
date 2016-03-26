# /test/test_conan.py
#
# Test cases for a "conan" container. We test this and the C++ variant
# in the same file so that they are not parallelized. This is because
# conan takes locks on files.
#
# See /LICENCE.md for Copyright information
"""Test cases for a conan container."""

import os

import platform

from test.testutil import (CIScriptExitsWith,
                           CapturedOutput,
                           WHICH_SCRIPT,
                           acceptance_test_for,
                           format_with_args)

import ciscripts.util as util

from nose_parameterized import parameterized

from testtools.matchers import (Contains, FileExists)

REQ_PROGRAMS = [
    "psq-travis-container-exec",
    "psq-travis-container-create"
]


class TestConanContainerSetup(acceptance_test_for("conan", REQ_PROGRAMS)):
    """Test cases for setting up a conan project container."""

    def tearDown(self):  # suppress(N802)
        """Remove build tree."""
        build = self.__class__.container.named_cache_dir("cmake-build")
        util.force_remove_tree(build)

        super(TestConanContainerSetup, self).tearDown()

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
        script = WHICH_SCRIPT.format(program)
        self.assertEqual(self.__class__.lang_container.execute(container,
                                                               output_strategy,
                                                               "python",
                                                               "-c",
                                                               script,
                                                               program),
                         0)

    def test_run_check_builds_cmake_project_success(self):
        """Running check script builds conan project."""
        self.assertThat("check/conan/check.py",
                        CIScriptExitsWith(0,
                                          self.__class__.container,
                                          self.__class__.util,
                                          "--no-mdl"))

    def test_run_check_builds_cmake_project_success_ninja(self):
        """Running check script with ninja generator builds conan project."""
        if platform.system() == "Windows" and os.environ.get("APPVEYOR",
                                                             None):
            self.skipTest("""Building ninja projects hangs on Windows""")

        self.assertThat("check/conan/check.py",
                        CIScriptExitsWith(0,
                                          self.__class__.container,
                                          self.__class__.util,
                                          "--no-mdl",
                                          "--generator",
                                          "Ninja"))

    def test_run_check_has_cmake_artifacts(self):
        """After running check, artifacts are present."""
        with CapturedOutput():
            check_path = "check/conan/check.py"
            check = self.__class__.container.fetch_and_import(check_path)

            check.run(self.__class__.container,
                      self.__class__.util,
                      None,
                      ["--no-mdl"])

        build = self.__class__.container.named_cache_dir("cmake-build")
        components = [build, "build"]

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


class TestPSQCPPContainerSetup(acceptance_test_for("psqcppconan",
                                                   REQ_PROGRAMS)):
    """Test cases for setting up a psqcppconan project container."""

    def tearDown(self):  # suppress(N802)
        """Remove build tree."""
        build = self.__class__.container.named_cache_dir("cmake-build")
        util.force_remove_tree(build)

        super(TestPSQCPPContainerSetup, self).tearDown()

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
        script = WHICH_SCRIPT.format(program)
        self.assertEqual(self.__class__.lang_container.execute(container,
                                                               output_strategy,
                                                               "python",
                                                               "-c",
                                                               script,
                                                               program),
                         0)

    def test_run_check_builds_cmake_project_success(self):
        """Running check script builds conan project."""
        self.assertThat("check/psqcppconan/check.py",
                        CIScriptExitsWith(0,
                                          self.__class__.container,
                                          self.__class__.util,
                                          "--no-mdl"))

    def test_run_check_builds_cmake_project_success_ninja(self):
        """Running check script with ninja generator builds conan project."""
        if platform.system() == "Windows" and os.environ.get("APPVEYOR",
                                                             None):
            self.skipTest("""Building ninja projects hangs on Windows""")

        self.assertThat("check/psqcppconan/check.py",
                        CIScriptExitsWith(0,
                                          self.__class__.container,
                                          self.__class__.util,
                                          "--no-mdl",
                                          "--generator",
                                          "Ninja"))

    def test_run_check_has_cmake_artifacts(self):
        """After running check, artifacts are present."""
        with CapturedOutput():
            check_path = "check/psqcppconan/check.py"
            check = self.__class__.container.fetch_and_import(check_path)

            check.run(self.__class__.container,
                      self.__class__.util,
                      None,
                      ["--no-mdl"])

        build = self.__class__.container.named_cache_dir("cmake-build")
        components = [build, "build"]

        # On Windows built binaries go into CMAKE_CFG_INTDIR, which
        # will be Debug in our case.
        if platform.system() == "Windows":
            binary_name = "psq_test.exe"
            components.append("Debug")
        else:
            binary_name = "psq_test"

        components.append(binary_name)
        self.assertThat(os.path.join(*components),
                        FileExists())

    def test_run_check_runs_test_binary(self):
        """Running check runs test binaries with expected output."""
        captured_output = CapturedOutput()
        with captured_output:
            check_path = "check/psqcppconan/check.py"
            check = self.__class__.container.fetch_and_import(check_path)

            check.run(self.__class__.container,
                      self.__class__.util,
                      None,
                      argv=[
                          "--no-mdl",
                          "--run-test-binaries",
                          "psq_test"
                      ])

        self.assertThat(captured_output.stderr,
                        Contains("ok 1 - pass"))
