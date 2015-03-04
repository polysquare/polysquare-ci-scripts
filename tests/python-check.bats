#!/usr/bin/env bats
# /tests/python-check.bats
#
# Ensure that the linting and testing facilities made available to us in
# lint.sh and test.sh work correctly.
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
load polysquare_container_copy_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/util.sh"

bootstrap="${POLYSQUARE_TRAVIS_SCRIPTS}/bootstrap.sh"
python_sample_project="${POLYSQUARE_TRAVIS_SCRIPTS}/../sample/python"

function python_setup {
    local sample_project_copy="$(mktemp -d /tmp/psq-python-project.XXXXXX)"

    cp -TRf "${python_sample_project}" "${sample_project_copy}"
    export _TEST_PYTHON_PROJECT="${sample_project_copy}"

    cd "${_TEST_PYTHON_PROJECT}"
    local container="${CONTAINER_DIR}"
    local boot=$(bash "${bootstrap}" -d "${container}" -s setup/python/setup.sh)
    eval "${boot}"
}

function python_teardown {
    rm -rf "${_TEST_PYTHON_PROJECT}"
}

@test "Find bugs with prospector" {
    python_setup

    # Create a line longer than 80 characters
    # shellcheck disable=SC2034
    for i in {1..10} ; do
        printf "abcfdefhijklmn" >> "${_TEST_PYTHON_PROJECT}/example/example.py"
    done

    printf " = 1\n" >> "${_TEST_PYTHON_PROJECT}/example/example.py"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/lint.sh"

    python_teardown

    [[ "${status}" == "1" ]]
    [[ "${lines[5]}" == "        example/example.py:" ]]
    [[ "${lines[6]}" == "            L7:80 None: pep8 - E501" ]]
    [[ "${lines[7]}" == "            line too long (144 > 79 characters)" ]]

}

@test "Find bugs with prospector on tests" {
    python_setup

    # Create a line longer than 80 characters
    # shellcheck disable=SC2034
    for i in {1..10} ; do
        printf "abcfdefhijklmn" >> "${_TEST_PYTHON_PROJECT}/tests/unit_test.py"
    done

    printf " = 1\n" >> "${_TEST_PYTHON_PROJECT}/tests/unit_test.py"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/lint.sh"

    python_teardown

    [[ "${status}" == "3" ]]
    [[ "${lines[5]}" == "        tests/unit_test.py:" ]]
    [[ "${lines[6]}" == "            L18:80 None: pep8 - E501" ]]
    [[ "${lines[7]}" == "            line too long (144 > 79 characters)" ]]
}

@test "Find bugs with flake8" {
    python_setup

    # Import module and never use it
    printf "\nimport sys  # pylint: disable=unused-import\n" >> \
        "${_TEST_PYTHON_PROJECT}/example/example.py"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/lint.sh"

    python_teardown

    echo "${output}"

    [[ "${status}" == "3" ]]
}

@test "Find bugs with pychecker" {
    python_setup

    local bug_file="${_TEST_PYTHON_PROJECT}/example/example.py"

    # Use integer division
    {
        printf "\n\ndef my_function():  # NOQA\n";
        printf "    return 1/3\n";
        printf "\n";
        printf "my_function()\n";
    } >> "${bug_file}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/lint.sh"

    python_teardown

    local int_div_warning=("        example/example.py:10:" \
                           "Using integer division (1 / 3) may return" \
                           "integer or float")

    [[ "${status}" == "1" ]]
    [[ "${lines[2]}" ==  "${int_div_warning[@]}" ]]
}

@test "Find unused functions with vulture" {
    python_setup

    local bug_file="${_TEST_PYTHON_PROJECT}/example/example.py"

    # Define a function and never use it
    {
        printf "\n\ndef _my_function():\n"
        printf "    pass\n"
    } >> "${bug_file}"

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/lint.sh"

    python_teardown

    [[ "${status}" == "1" ]]
    [[ "${lines[6]}" == "        example/example.py:" ]]
    [[ "${lines[7]}" == "            L9:- None: vulture - unused-function" ]]
    [[ "${lines[8]}" == "            Unused function _my_function" ]]
}

@test "Success on no bugs found" {
    python_setup

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/lint.sh"

    python_teardown

    [[ "${status}" == "0" ]]
}

@test "Run unit tests" {
    python_setup

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/test.sh" -m example

    python_teardown

    echo "${output}"

    [[ "${status}" == "0" ]]
    [[ "${lines[11]}" == "    test_simple_case (tests.unit_test.TestUnit)" ]]
    [[ "${lines[12]}" == \
       "    tests.unit_test.TestUnit.test_simple_case ... ok" ]]
}

@test "Run unit tests and make coverage report" {
    python_setup

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/test.sh"  -m example
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/coverage.sh"

    python_teardown

    [[ "${status}" == "0" ]]
    [[ "${lines[2]}" == \
       "        Name               Stmts   Miss  Cover   Missing" ]]
    [[ "${lines[7]}" == \
       "TOTAL                  2      1    50%   " ]]
}

@test "Install python project" {
    python_setup

    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/check/python/install.sh"

    [[ "${status}" == "0" ]]
    [[ "${lines[1]}" == "    running install" ]]
}
