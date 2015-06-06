# /test/test_project.py
#
# Test cases for a "project" container.
#
# See /LICENCE.md for Copyright information
"""Test cases for a project container."""

import os

import tempfile

from test.testutil import (CIScriptExitsWith,
                           acceptance_test_for)

LICENCE_STRING = "See /LICENCE.md for Copyright information"


def write_valid_header(f):
    """Write a valid header to file."""
    file_path = os.path.abspath(f.name)
    common_prefix = os.path.commonprefix([file_path, os.getcwd()])
    header_path = file_path[len(common_prefix):].replace("\\", "/")
    f.write("#!/bin/bash\n"
            "# {path}\n"
            "#\n"
            "# Description\n"
            "#\n"
            "# {licence}\n\n".format(path=header_path,
                                     licence=LICENCE_STRING))


def write_invalid_header(f):
    """Write a invalid header to file."""
    file_path = os.path.abspath(f.name)
    common_prefix = os.path.commonprefix([file_path, os.getcwd()])
    header_path = file_path[len(common_prefix):].replace("\\", "/")
    f.write("#!/bin/bash\n"
            "# error-{path}\n"
            "#\n"
            "# Description\n"
            "#\n"
            "# {licence}\n".format(path=header_path,
                                   licence=LICENCE_STRING))
    f.flush()


class TestProjectContainerSetup(acceptance_test_for("project", [])):

    """Test cases for setting up a project container."""

    def test_lint_with_style_guide_linter_success(self):
        """Success code if all files satisfy style guide linter."""
        with open(os.path.join(os.getcwd(), "success.sh"),
                  "wt") as success_file:
            write_valid_header(success_file)

        self.assertThat("check/project/lint.py",
                        CIScriptExitsWith(0,
                                          self.__class__.container,
                                          self.__class__.util,
                                          extensions=["sh"],
                                          no_mdl=True))

    def test_lint_with_style_guide_linter_failure(self):
        """Failure code if one file doesn't satisfy style guide linter."""
        with open(os.path.join(os.getcwd(), "failure.sh"),
                  "wt") as failure_file:
            write_invalid_header(failure_file)

        self.assertThat("check/project/lint.py",
                        CIScriptExitsWith(1,
                                          self.__class__.container,
                                          self.__class__.util,
                                          extensions=["sh"],
                                          no_mdl=True))

    def test_lint_files_in_multiple_subdirectories(self):
        """Style guide linter runs over multiple subdirectories."""
        success_dir = tempfile.mkdtemp(dir=os.getcwd())
        failure_dir = tempfile.mkdtemp(dir=os.getcwd())

        with open(os.path.join(success_dir, "success.sh"),
                  "wt") as success_file:
            write_valid_header(success_file)

        with open(os.path.join(failure_dir, "failure.sh"),
                  "wt") as failure_file:
            write_invalid_header(failure_file)

        self.assertThat("check/project/lint.py",
                        CIScriptExitsWith(1,
                                          self.__class__.container,
                                          self.__class__.util,
                                          extensions=["sh"],
                                          directories=[success_dir,
                                                       failure_dir],
                                          no_mdl=True))

    def test_lint_files_with_multiple_extensions(self):
        """Style guide linter runs over multiple extensions."""
        with open(os.path.join(os.getcwd(), "success.zh"),
                  "wt") as success_file:
            write_valid_header(success_file)

        with open(os.path.join(os.getcwd(), "failure.sh"),
                  "wt") as failure_file:
            write_invalid_header(failure_file)

        self.assertThat("check/project/lint.py",
                        CIScriptExitsWith(1,
                                          self.__class__.container,
                                          self.__class__.util,
                                          extensions=["sh"],
                                          no_mdl=True))

    def test_files_can_be_excluded_from_linting(self):
        """Exclude certain files from style guide linter."""
        with open(os.path.join(os.getcwd(), "success.zh"),
                  "wt") as success_file:
            write_valid_header(success_file)

        with open(os.path.join(os.getcwd(), "failure.sh"),
                  "wt") as failure_file:
            write_invalid_header(failure_file)

        fail_path = os.path.realpath(failure_file.name)

        self.assertThat("check/project/lint.py",
                        CIScriptExitsWith(0,
                                          self.__class__.container,
                                          self.__class__.util,
                                          extensions=["sh"],
                                          exclusions=[fail_path],
                                          no_mdl=True))

    def test_many_files_can_be_excluded_from_linting(self):
        """Exclude many files from style guide linting."""
        with open(os.path.join(os.getcwd(), "success.sh"),
                  "wt") as success_file:
            write_valid_header(success_file)

        with open(os.path.join(os.getcwd(), "failure.zh"),
                  "wt") as failure_file:
            write_invalid_header(failure_file)

        with open(os.path.join(os.getcwd(), "2failure.zh"),
                  "wt") as second_failure_file:
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
                                          ],
                                          no_mdl=True))

    def test_linting_of_markdown_documentation_with_success(self):
        """Lint markdown documentation with success exit code."""
        if os.environ.get("APPVEYOR", None):
            self.skipTest("""installation of mdl is too slow on appveyor""")

        with open(os.path.join(os.getcwd(), "documentation.md"), "wt"):
            self.assertThat("check/project/lint.py",
                            CIScriptExitsWith(0,
                                              self.__class__.container,
                                              self.__class__.util,
                                              extensions=["other"]))

    def test_linting_of_markdown_documentation_with_failure(self):
        """Lint markdown documentation with failure exit code."""
        if os.environ.get("APPVEYOR", None):
            self.skipTest("""installation of mdl is too slow on appveyor""")

        with open(os.path.join(os.getcwd(), "documentation.md"),
                  "wt") as markdown_file:
            markdown_file.write("Level One\n==\n\n## Level Two ##\n")
            markdown_file.flush()

        self.assertThat("check/project/lint.py",
                        CIScriptExitsWith(1,
                                          self.__class__.container,
                                          self.__class__.util,
                                          extensions=["other"]))
