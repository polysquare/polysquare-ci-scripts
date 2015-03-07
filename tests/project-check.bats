#!/usr/bin/env bats
# /tests/project-check.bats
#
# Tests for the linting functions in check/project/lint.sh
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
load polysquare_container_copy_helper
load polysquare_project_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/util.sh"

setup() {
    polysquare_container_copy_setup
    polysquare_project_setup

    local directory="${_POLYSQUARE_TEST_PROJECT}"

    export _PROJECT_FILE_TO_LINT=$(mktemp "${directory}/test-XXXXXX.sh")
}

teardown() {
    unset _PROJECT_FILE_TO_LINT

    polysquare_project_teardown
    polysquare_container_copy_teardown
}

licence="See LICENCE.md for Copyright information"

function write_valid_header_to {
    local file="$1"
    local pwd_name_length="${#PWD}"
    local expected_filename="${file:$pwd_name_length}"

    printf "#!/bin/bash\n# %s\n#\n# Description\n#\n# %s\n\n" \
        "${expected_filename}" "${licence}" > "${file}"
}

function write_invalid_header_to {
    local file="$1"
    local pwd_name_length="${#PWD}"
    local expected_filename="${file:$pwd_name_length}"

    printf "#!/bin/bash\n# %s-error\n#\n# Description\n#\n# %s\n\n" \
        "${expected_filename}" "${licence}" > "${file}"
}

@test "Lint files with success using style-guide-linter" {
    # Valid header
    write_valid_header_to "${_PROJECT_FILE_TO_LINT}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/project/lint.sh" \
        -d "${_POLYSQUARE_TEST_PROJECT}" -e sh

    [ "${status}" == "0" ]
}

@test "Lint files with failure using style-guide-linter" {
    # Invalid header
    write_invalid_header_to "${_PROJECT_FILE_TO_LINT}"
    
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/project/lint.sh" \
        -d "${_POLYSQUARE_TEST_PROJECT}" -e sh

    [ "${status}" == "1" ]
}

@test "Lint files in multiple directories" {
    local directory_one=$(mktemp -d "${_POLYSQUARE_TEST_PROJECT}/1.XXXXXX")
    local project_file_to_lint_one=$(mktemp "${directory_one}/test-XXXXXX.sh")

    local directory_two=$(mktemp -d "${_POLYSQUARE_TEST_PROJECT}/2.XXXXXX")
    local project_file_to_lint_two=$(mktemp "${directory_two}/test-XXXXXX.sh")

    # Enter the test project directory, since we're linting two different
    # subdirs from there
    pushd "${_POLYSQUARE_TEST_PROJECT}"
    rm -f "${_PROJECT_FILE_TO_LINT}"

    # Script in first directory valid, script in second invalid. Make sure
    # we get the invalid script.
    write_valid_header_to "${project_file_to_lint_one}"
    write_invalid_header_to "${project_file_to_lint_two}"

    # Run with both directories
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/project/lint.sh" \
        -d "${directory_one}" -d "${directory_two}" -e sh

    [ "${status}" == "1" ]
}

@test "Lint files with multiple extensions" {
    local directory="${_POLYSQUARE_TEST_PROJECT}"
    local project_file_to_lint_one=$(mktemp "${directory}/test-XXXXXX.sh")
    local project_file_to_lint_two=$(mktemp "${directory}/test-XXXXXX.bash")

    pushd "${directory}"
    rm -f "${_PROJECT_FILE_TO_LINT}"

    # Script in first directory valid, script in second invalid. Make sure
    # we get the invalid script.

    write_valid_header_to "${project_file_to_lint_one}"
    write_invalid_header_to "${project_file_to_lint_two}"

    # Run with both extensions
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/project/lint.sh" \
        -d "${directory}" -e sh -e bash

    [ "${status}" == "1" ]
}

@test "Exclude one file from linting" {
    local directory_one=$(mktemp -d "${_POLYSQUARE_TEST_PROJECT}/1.XXXXXX")
    local project_file_to_lint_one=$(mktemp "${directory_one}/test-XXXXXX.sh")

    local directory_two=$(mktemp -d "${_POLYSQUARE_TEST_PROJECT}/2.XXXXXX")
    local project_file_to_lint_two=$(mktemp "${directory_two}/test-XXXXXX.sh")

    # Enter the test project directory, since we're linting two different
    # subdirs from there
    pushd "${_POLYSQUARE_TEST_PROJECT}"
    rm -f "${_PROJECT_FILE_TO_LINT}"

    # Script in first directory valid, script in second invalid. Make sure
    # we get the invalid script.
    write_valid_header_to "${project_file_to_lint_one}"
    write_invalid_header_to "${project_file_to_lint_two}"

    # Run with both directories, but exclude the second file. Result should
    # be success as we have skipped the second (broken) file.
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/project/lint.sh" \
        -d "${directory_one}" -d "${directory_two}" -e sh \
            -x "${project_file_to_lint_two}"

    [ "${status}" == "0" ]
}

@test "Exclude many files from linting" {
    local directory_one=$(mktemp -d "${_POLYSQUARE_TEST_PROJECT}/1.XXXXXX")
    local project_file_to_lint_one=$(mktemp "${directory_one}/test-XXXXXX.sh")

    local directory_two=$(mktemp -d "${_POLYSQUARE_TEST_PROJECT}/2.XXXXXX")
    local project_file_to_lint_two=$(mktemp "${directory_two}/test-XXXXXX.sh")
    local project_file_to_lint_three=$(mktemp "${directory_two}/test-XXXXXX.sh")

    # Enter the test project directory, since we're linting two different
    # subdirs from there
    pushd "${_POLYSQUARE_TEST_PROJECT}"
    rm -f "${_PROJECT_FILE_TO_LINT}"

    # Script in first directory valid, script in second invalid. Make sure
    # we get the invalid script.
    write_valid_header_to "${project_file_to_lint_one}"
    write_invalid_header_to "${project_file_to_lint_two}"
    write_invalid_header_to "${project_file_to_lint_three}"

    # Run with both directories, but exclude the second and third files. Result
    # should be success as we have skipped the second and third (broken) files.
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/project/lint.sh" \
        -d "${directory_one}" -d "${directory_two}" -e sh \
            -x "${project_file_to_lint_two}" \
            -x "${project_file_to_lint_three}"

    [ "${status}" == "0" ]
}

@test "Lint markdown documentation with success using mdl" {
    rm -f "${_PROJECT_FILE_TO_LINT}"

    # Valid markdown documentation
    markdown_doc=$(mktemp "${_POLYSQUARE_TEST_PROJECT}/Documentation.XXXXXX.md")

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/project/lint.sh" \
        -d "${_POLYSQUARE_TEST_PROJECT}" -e sh

    [ "${status}" == "0" ]
}

@test "Lint markdown documentation with failure using mdl" {
    rm -f "${_PROJECT_FILE_TO_LINT}"

    # Invalid markdown documentation
    markdown_doc=$(mktemp "${_POLYSQUARE_TEST_PROJECT}/Documentation.XXXXXX.md")
    printf "H1\n==\n## H2 ##\n" > "${markdown_doc}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/project/lint.sh" \
        -d "${_POLYSQUARE_TEST_PROJECT}" -e sh

    [ "${status}" == "1" ]
}

