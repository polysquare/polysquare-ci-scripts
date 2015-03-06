#!/usr/bin/env bats
# /tests/project-setup.bats
#
# Tests for setup/project/project.sh - checking to make sure certain utilities
# are installed after the setup script has been run.
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
load polysquare_container_copy_helper
load polysquare_project_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/util.sh"

setup() {
    polysquare_container_copy_setup
    polysquare_project_setup
}

teardown() {
    polysquare_project_teardown
    polysquare_container_copy_teardown
}

@test "Polysquare style guide linter is available after running setup script" {
    run which polysquare-generic-file-linter

    [ "${status}" == "0" ]
}

@test "Markdownlint is available after running setup script" {
    run which mdl

    [ "${status}" == "0" ]
}
