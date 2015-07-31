# /test/test_bii.py
#
# Test cases for a "bii" container.
#
# See /LICENCE.md for Copyright information
"""Test cases for a bii container."""

import os

import platform

from test.testutil import (CIScriptExitsWith,
                           CapturedOutput,
                           WHICH_SCRIPT,
                           acceptance_test_for,
                           format_with_args)

import ciscripts.util as util

from nose_parameterized import parameterized

from testtools.matchers import FileExists

REQ_PROGRAMS = [
    "psq-travis-container-exec",
    "psq-travis-container-create",
    "bii"
]


class TestBiiContainerSetup(acceptance_test_for("bii", REQ_PROGRAMS)):

    """Test cases for setting up a bii project container."""

    def tearDown(self):  # suppress(N802)
        """Remove build tree."""
        build = self.__class__.container.named_cache_dir("cmake-build")
        util.force_remove_tree(build)

        super(TestBiiContainerSetup, self).tearDown()

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
        """Running check script builds bii project."""
        self.assertThat("check/bii/check.py",
                        CIScriptExitsWith(0,
                                          self.__class__.container,
                                          self.__class__.util,
                                          "--no-mdl",
                                          "--block",
                                          "polysquare/test"))

    def test_run_check_has_cmake_artifacts(self):
        """After running check, artifacts are present."""
        with CapturedOutput():
            check_path = "check/bii/check.py"
            check = self.__class__.container.fetch_and_import(check_path)

            check.run(self.__class__.container,
                      self.__class__.util,
                      None,
                      ["--no-mdl",
                       "--block",
                       "polysquare/test"])

        build = self.__class__.container.named_cache_dir("cmake-build")
        components = [build, "bin"]

        # On Windows built binaries go into CMAKE_CFG_INTDIR, which
        # will be Debug in our case.
        if platform.system() == "Windows":
            binary_name = "my_executable.exe"
        else:
            binary_name = "my_executable"

        components.append(binary_name)
        self.assertThat(os.path.join(*components),
                        FileExists())
