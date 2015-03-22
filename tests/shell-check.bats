#!/usr/bin/env bats
# /tests/shell-check.bats
#
# Tests for the checking functions in shell/check/lint.sh
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
load polysquare_container_copy_helper
load polysquare_shell_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/util.sh"

setup() {
    polysquare_container_copy_setup
    polysquare_shell_setup

    export _SHELL_FILE_TO_LINT="${_POLYSQUARE_TEST_PROJECT}/example.sh"
    printf "#!/bin/bash\necho hello\n" > "${_SHELL_FILE_TO_LINT}"
}

teardown() {
    polysquare_shell_teardown
    polysquare_container_copy_teardown
}

@test "Lint shell files with success" {
    # Valid shell script
    printf "#!/bin/bash\necho hello\n" > "${_SHELL_FILE_TO_LINT}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/shell/lint.sh" \
        -d "${_POLYSQUARE_TEST_PROJECT}"

    [ "${status?}" == "0" ]
}

@test "Lint shell files with failure" {
    # Valid shell script
    printf "echo hello\n" > "${_SHELL_FILE_TO_LINT}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/shell/lint.sh" \
        -d "${_POLYSQUARE_TEST_PROJECT}"

    [ "${status?}" == "1" ]
}

@test "Lint bash files with failure" {
    local directory="${_POLYSQUARE_TEST_PROJECT}"
    local -r shell_file_to_lint=$(mktemp "${directory}/test-XXXXXX.bash")

    # Invalid shell script
    printf "echo hello\n" > "${shell_file_to_lint}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/shell/lint.sh" \
        -d "${directory}"

    [ "${status?}" == "1" ]
}

@test "Lint bats files with failure" {
    local directory="${_POLYSQUARE_TEST_PROJECT}"
    local -r shell_file_to_lint=$(mktemp "${directory}/test-XXXXXX.bats")

    # Invalid shell script
    printf "echo hello\n" > "${shell_file_to_lint}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/shell/lint.sh" \
        -d "${directory}"

    [ "${status?}" == "1" ]
}

@test "Lint bats files with success, even with bats-like syntax" {
    local directory="${_POLYSQUARE_TEST_PROJECT}"
    local -r shell_file_to_lint=$(mktemp "${directory}/test-XXXXXX.bats")

    # BATS script. This should be pre-processed and converted into something
    # else before it is run through shellcheck and bashlint.
    printf "#!/usr/bin/env bats\n@test \"t\" {\n}\n" > "${shell_file_to_lint}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/shell/lint.sh" \
        -d "${directory}"

    [ "${status?}" == "0" ]
}

@test "Lint files in multiple directories" {
    local -r directory_one=$(mktemp -d "${_POLYSQUARE_TEST_PROJECT}/1.XXXXXX")
    local -r shell_file_to_lint_one=$(mktemp "${directory_one}/test-XXXXXX.sh")

    local -r directory_two=$(mktemp -d "${_POLYSQUARE_TEST_PROJECT}/2.XXXXXX")
    local -r shell_file_to_lint_two=$(mktemp "${directory_two}/test-XXXXXX.sh")

    # Script in first directory valid, script in second invalid. Make sure
    # we get the invalid script.
    printf "#!/bin/bash\necho hello\n" > "${shell_file_to_lint_one}"
    printf "echo hello\n" > "${shell_file_to_lint_two}"

    # Run with both directories
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/shell/lint.sh" \
        -d "${directory_one}" -d "${directory_two}"

    [ "${status?}" == "1" ]
}

@test "Lint shell files with failure" {
    # No shebang - fail
    printf "echo hello\n" > "${_SHELL_FILE_TO_LINT}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/shell/lint.sh" \
        -d "${_POLYSQUARE_TEST_PROJECT}"

    [ "${status?}" == "1" ]
}

# Sadly, it isn't possible to test the invocation of BATS tests at the moment

