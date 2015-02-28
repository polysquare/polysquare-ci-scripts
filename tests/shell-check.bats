#!/usr/bin/env bats
# /tests/shell-check.bats
#
# Tests for the utility functions in travis/
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/util.sh"

function lint_setup {
    local directory_var="$1"
    local shell_file_to_lint_var="$2"

    local _directory=$(mktemp -d /tmp/psq-lint-shell-test.XXXXXX)
    local _shell_file_to_lint=$(mktemp "${_directory}/test-XXXXXX.sh")

    eval "${directory_var}='${_directory}'"
    eval "${shell_file_to_lint_var}='${_shell_file_to_lint}'"
}

function lint_teardown {
    local directory="$1"

    rm -rf "${directory}"
}

@test "Lint shell files with success" {
    lint_setup directory shell_file_to_lint

    # Valid shell script
    printf "#!/bin/bash\necho hello\n" > "${shell_file_to_lint}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/shell/lint.sh" \
        -d "${directory}"

    lint_teardown "${directory}"

    [ "${status}" == "0" ]
}

@test "Lint bash files with failure" {
    local directory=$(mktemp -d /tmp/psq-lint-shell-test.XXXXXX)
    local shell_file_to_lint=$(mktemp "${directory}/test-XXXXXX.bash")

    # Invalid shell script
    printf "echo hello\n" > "${shell_file_to_lint}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/shell/lint.sh" \
        -d "${directory}"

    lint_teardown "${directory}"

    [ "${status}" == "1" ]
}

@test "Lint bats files with failure" {
    local directory=$(mktemp -d /tmp/psq-lint-shell-test.XXXXXX)
    local shell_file_to_lint=$(mktemp "${directory}/test-XXXXXX.bats")

    # Invalid shell script
    printf "echo hello\n" > "${shell_file_to_lint}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/shell/lint.sh" \
        -d "${directory}"

    lint_teardown "${directory}"

    [ "${status}" == "1" ]
}

@test "Lint bats files with success, even with bats-like syntax" {
    local directory=$(mktemp -d /tmp/psq-lint-shell-test.XXXXXX)
    local shell_file_to_lint=$(mktemp "${directory}/test-XXXXXX.bats")

    # BATS script. This should be pre-processed and converted into something
    # else before it is run through shellcheck and bashlint.
    printf "#!/usr/bin/env bats\n@test \"t\" {\n}\n" > "${shell_file_to_lint}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/shell/lint.sh" \
        -d "${directory}"

    lint_teardown "${directory}"

    [ "${status}" == "0" ]
}

@test "Lint files in multiple directories" {
    local directory_one=$(mktemp -d /tmp/psq-lint-shell-test.XXXXXX)
    local shell_file_to_lint_one=$(mktemp "${directory_one}/test-XXXXXX.sh")

    local directory_two=$(mktemp -d /tmp/psq-lint-shell-test.XXXXXX)
    local shell_file_to_lint_two=$(mktemp "${directory_two}/test-XXXXXX.sh")

    # Script in first directory valid, script in second invalid. Make sure
    # we get the invalid script.
    printf "#!/bin/bash\necho hello\n" > "${shell_file_to_lint_one}"
    printf "echo hello\n" > "${shell_file_to_lint_two}"

    # Run with both directories
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/shell/lint.sh" \
        -d "${directory_one}" -d "${directory_two}"

    lint_teardown "${directory}"

    [ "${status}" == "1" ]
}

@test "Lint shell files with failure" {
    lint_setup directory shell_file_to_lint

    # No shebang - fail
    printf "echo hello\n" > "${shell_file_to_lint}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/shell/lint.sh" \
        -d "${directory}"

    lint_teardown "${directory}"

    [ "${status}" == "1" ]
}

# Sadly, it isn't possible to test the invocation of BATS tests at the moment

