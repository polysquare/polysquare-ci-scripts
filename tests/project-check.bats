#!/usr/bin/env bats
# /tests/project-check.bats
#
# Tests for the linting functions in check/project/lint.sh
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/util.sh"

function lint_setup {
    local directory_var="$1"
    local project_file_to_lint_var="$2"

    local _directory=$(mktemp -d /tmp/psq-lint-shell-test.XXXXXX)
    local _project_file_to_lint=$(mktemp "${_directory}/test-XXXXXX.sh")

    pushd "${_directory}" > /dev/null 2>&1

    eval "${directory_var}='${_directory}'"
    eval "${project_file_to_lint_var}='${_project_file_to_lint}'"
}

function lint_teardown {
    popd > /dev/null 2>&1

    for directory in "$@" ; do
        rm -rf "${directory}"
    done
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
    lint_setup directory project_file_to_lint

    # Valid header
    write_valid_header_to "${project_file_to_lint}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/project/lint.sh" \
        -d "${directory}" -e sh

    [ "${status}" == "0" ]

    lint_teardown "${directory}"
}

@test "Lint files with failure using style-guide-linter" {
    lint_setup directory project_file_to_lint

    # Invalid header
    write_invalid_header_to "${project_file_to_lint}"
    
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/project/lint.sh" \
        -d "${directory}" -e sh

    [ "${status}" == "1" ]

    lint_teardown "${directory}"
}

@test "Lint files in multiple directories" {
    local directory_one=$(mktemp -d /tmp/psq-lint-shell-test.XXXXXX)
    local project_file_to_lint_one=$(mktemp "${directory_one}/test-XXXXXX.sh")

    local directory_two=$(mktemp -d /tmp/psq-lint-shell-test.XXXXXX)
    local project_file_to_lint_two=$(mktemp "${directory_two}/test-XXXXXX.sh")

    # Enter the "/tmp" directory, since we're linting two different subdirs
    # from there
    pushd "/tmp"

    # Script in first directory valid, script in second invalid. Make sure
    # we get the invalid script.
    write_valid_header_to "${project_file_to_lint_one}"
    write_invalid_header_to "${project_file_to_lint_two}"

    # Run with both directories
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/project/lint.sh" \
        -d "${directory_one}" -d "${directory_two}" -e sh

    [ "${status}" == "1" ]

    lint_teardown "${directory_one}" "${directory_two}"
}

@test "Lint files with multiple extensions" {
    local directory=$(mktemp -d /tmp/psq-lint-shell-test.XXXXXX)
    local project_file_to_lint_one=$(mktemp "${directory}/test-XXXXXX.sh")
    local project_file_to_lint_two=$(mktemp "${directory}/test-XXXXXX.bash")

    pushd "${directory}"

    # Script in first directory valid, script in second invalid. Make sure
    # we get the invalid script.
    write_valid_header_to "${project_file_to_lint_one}"
    write_invalid_header_to "${project_file_to_lint_two}"

    # Run with both extensions
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/project/lint.sh" \
        -d "${directory}" -e sh -e bash

    [ "${status}" == "1" ]

    lint_teardown "${directory}"
}

@test "Exclude one file from linting" {
    local directory_one=$(mktemp -d /tmp/psq-lint-shell-test.XXXXXX)
    local project_file_to_lint_one=$(mktemp "${directory_one}/test-XXXXXX.sh")

    local directory_two=$(mktemp -d /tmp/psq-lint-shell-test.XXXXXX)
    local project_file_to_lint_two=$(mktemp "${directory_two}/test-XXXXXX.sh")

    pushd "/tmp"

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

    lint_teardown "${directory}"
}

@test "Exclude many files from linting" {
    local directory_one=$(mktemp -d /tmp/psq-lint-shell-test.XXXXXX)
    local project_file_to_lint_one=$(mktemp "${directory_one}/test-XXXXXX.sh")

    local directory_two=$(mktemp -d /tmp/psq-lint-shell-test.XXXXXX)
    local project_file_to_lint_two=$(mktemp "${directory_two}/test-XXXXXX.sh")
    local project_file_to_lint_three=$(mktemp "${directory_two}/test-XXXXXX.sh")

    pushd "/tmp"

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

    lint_teardown "${directory}"
}

@test "Lint markdown documentation with success using mdl" {
    lint_setup directory project_file_to_lint
    rm -rf "${project_file_to_lint}"

    # Valid markdown documentation
    markdown_doc=$(mktemp "${directory}/Documentation.XXXXXX.md")

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/project/lint.sh" \
        -d "${directory}" -e sh

    [ "${status}" == "0" ]

    lint_teardown "${directory}"
}

@test "Lint markdown documentation with failure using mdl" {
    lint_setup directory project_file_to_lint
    rm -rf "${project_file_to_lint}"

    # Invalid markdown documentation
    markdown_doc=$(mktemp "${directory}/Documentation.XXXXXX.md")
    printf "H1\n==\n## H2 ##\n" > "${markdown_doc}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/project/lint.sh" \
        -d "${directory}" -e sh

    [ "${status}" == "1" ]

    lint_teardown "${directory}"
}

