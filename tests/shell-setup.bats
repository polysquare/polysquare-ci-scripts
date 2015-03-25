#!/usr/bin/env bats
# /tests/shell-setup.bats
#
# Tests for setup/shell/setup.sh - checking to make sure certain utilities
# are installed after the setup script has been run.
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
load polysquare_container_copy_helper
load polysquare_shell_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/util.sh"

setup() {
    polysquare_container_copy_setup
    polysquare_shell_setup
}

teardown() {
    polysquare_shell_teardown
    polysquare_container_copy_teardown
}

@test "Shellcheck is available after running bash setup script" {
    run which shellcheck

    [ "${status?}" == "0" ]
}

@test "Bashlint is available after running bash setup script" {
    run which bashlint

    [ "${status?}" == "0" ]
}

@test "BATS is available after running bash setup script" {
    run which bats

    [ "${status?}" == "0" ]
}

@test "Bashcov is available after running bash setup script" {
    run which bats

    [ "${status?}" == "0" ]
}
