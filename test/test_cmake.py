# /test/test_cmake.py
#
# Test cases for a "project" container.
#
# See /LICENCE.md for Copyright information
"""Test cases for a project container."""

import os

import platform

import shutil

from test.testutil import (CIScriptExitsWith,
                           CapturedOutput,
                           WHICH_SCRIPT,
                           acceptance_test_for,
                           copy_scripts_to_directory,
                           format_with_args)

import ciscripts.util as util

from nose_parameterized import parameterized

from testtools.matchers import FileExists

REQ_PROGRAMS = [
    "psq-travis-container-exec",
    "psq-travis-container-create"
]

__file__ = os.path.abspath(__file__)


class TestCMakeContainerSetup(acceptance_test_for("cmake", REQ_PROGRAMS)):

    """Test cases for setting up a cmake project container."""

    def tearDown(self):  # suppress(N802)
        """Remove build tree."""
        shutil.rmtree(self.__class__.container.named_cache_dir("cmake-build"))

        super(TestCMakeContainerSetup, self).tearDown()

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
        copy_scripts_to_directory(os.getcwd())
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
        with CapturedOutput():
            check_path = "check/cmake/check.py"
            check = self.__class__.container.fetch_and_import(check_path)

            check.run(self.__class__.container,
                      self.__class__.util,
                      None,
                      ["--no-mdl"])

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
