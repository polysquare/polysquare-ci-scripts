#!/usr/bin/env bats
# /tests/python-check.bats
#
# Ensure that the linting and testing facilities made available to us in
# lint.sh and test.sh work correctly.
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
load polysquare_container_copy_helper
load polysquare_python_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/util.sh"

setup() {
    polysquare_python_setup
    polysquare_container_copy_setup
}

teardown() {
    polysquare_container_copy_teardown
    polysquare_python_teardown
}

@test "Find bugs with prospector" {
    # Create a line longer than 80 characters
    # shellcheck disable=SC2034
    for i in {1..20} ; do
        printf "abcfdefhijk" >> "${_POLYSQUARE_TEST_PROJECT}/example/example.py"
    done

    printf " = 1\n" >> "${_POLYSQUARE_TEST_PROJECT}/example/example.py"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/lint.sh"

    [[ "${status?}" == "1" ]]

    # shellcheck disable=SC2154
    [[ "${lines[5]}" == "        example/example.py:" ]]

    # shellcheck disable=SC2154
    [[ "${lines[6]}" == "            L7:80 None: pep8 - E501" ]]

    # shellcheck disable=SC2154
    [[ "${lines[7]}" == "            line too long (224 > 79 characters)" ]]
}

@test "Find bugs with prospector on tests" {
    # Create a line longer than 80 characters
    # shellcheck disable=SC2034
    for i in {1..20} ; do
        printf "abcfdefhijk" >> "${_POLYSQUARE_TEST_PROJECT}/tests/unit_test.py"
    done

    printf " = 1\n" >> "${_POLYSQUARE_TEST_PROJECT}/tests/unit_test.py"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/lint.sh"

    [[ "${status?}" == "3" ]]

    # shellcheck disable=SC2154
    [[ "${lines[5]}" == "        tests/unit_test.py:" ]]

    # shellcheck disable=SC2154
    [[ "${lines[6]}" == "            L18:80 None: pep8 - E501" ]]

    # shellcheck disable=SC2154
    [[ "${lines[7]}" == "            line too long (224 > 79 characters)" ]]
}

@test "Find bugs with flake8" {
    # Import module and never use it
    printf "\nimport sys  # pylint: disable=unused-import\n" >> \
        "${_POLYSQUARE_TEST_PROJECT}/example/example.py"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/lint.sh"

    [[ "${status?}" == "3" ]]
}

@test "Find bugs with pychecker" {
    local bug_file="${_POLYSQUARE_TEST_PROJECT}/example/example.py"

    # Use integer division
    {
        printf "\n\ndef my_function():  # NOQA\n";
        printf "    return 1/3\n";
        printf "\n";
        printf "my_function()\n";
    } >> "${bug_file}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/lint.sh"

    local int_div_warning=("        example/example.py:10:" \
                           "Using integer division (1 / 3) may return" \
                           "integer or float")

    [[ "${status?}" == "1" ]]
    [[ "${lines[2]}" ==  "${int_div_warning[@]}" ]] # shellcheck disable=SC2154
}

@test "Find unused functions with vulture" {
    local bug_file="${_POLYSQUARE_TEST_PROJECT}/example/example.py"

    # Define a function and never use it
    {
        printf "\n\ndef _my_function():\n"
        printf "    pass\n"
    } >> "${bug_file}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/lint.sh"

    [[ "${status?}" == "1" ]]

    # shellcheck disable=SC2154
    [[ "${lines[6]}" == "        example/example.py:" ]]

    # shellcheck disable=SC2154
    [[ "${lines[7]}" == "            L9:- None: vulture - unused-function" ]]

    # shellcheck disable=SC2154
    [[ "${lines[8]}" == "            Unused function _my_function" ]]
}

@test "Success on no bugs found" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/lint.sh"

    [[ "${status?}" == "0" ]]
}

@test "Run unit tests" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/test.sh" -m example

    [[ "${status?}" == "0" ]]

    # shellcheck disable=SC2154
    [[ "${lines[11]}" == "    test_simple_case (tests.unit_test.TestUnit)" ]]

    # shellcheck disable=SC2154
    [[ "${lines[12]}" == \
       "    tests.unit_test.TestUnit.test_simple_case ... ok" ]]
}

@test "Run unit tests and make coverage report" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/test.sh"  -m example
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/coverage.sh"

    [[ "${status?}" == "0" ]]

    # shellcheck disable=SC2154
    [[ "${lines[2]}" == \
       "        Name               Stmts   Miss  Cover   Missing" ]]

    # shellcheck disable=SC2154
    [[ "${lines[7]}" == \
       "        TOTAL                  2      1    50%   " ]]
}

@test "Install python project" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/install.sh"

    [[ "${status?}" == "0" ]]
    [[ "${lines[1]}" == "    running install" ]] # shellcheck disable=SC2154

    run python setup.py uninstall
}
