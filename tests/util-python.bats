#!/usr/bin/env bats
# /tests/util-python.bats
#
# Tests for the utility functions in travis/
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/python-util.sh"

@test "Get python version" {
    local python_version
    polysquare_get_python_version python_version

    [[ "${python_version}" =~ ^[1-9]\.[1-9]\.[1-9]$ ]]
}

@test "Run command if python module unavailable" {
    run polysquare_run_if_python_module_unavailable __unavailable echo "true"

    [[ "${output}" == "true" ]]
}

@test "Dont run command if python module available" {
    run polysquare_run_if_python_module_unavailable sys echo "true"

    [[ "${output}" == "" ]]
}
