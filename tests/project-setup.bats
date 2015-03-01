#!/usr/bin/env bats
# /tests/project-setup.bats
#
# Tests for setup/project/project.sh - checking to make sure certain utilities
# are installed after the setup script has been run.
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
load polysquare_container_copy_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/util.sh"

bootstrap="${POLYSQUARE_TRAVIS_SCRIPTS}/bootstrap.sh"

function project_setup {
    local cont="${CONTAINER_DIR}"
    local boot=$(bash "${bootstrap}" -d "${cont}" -s setup/project/setup.sh)
    eval "${boot}"
}

@test "Polysquare style guide linter is available after running setup script" {
    project_setup

    run which polysquare-generic-file-linter

    [ "${status}" == "0" ]
}

@test "Markdownlint is available after running setup script" {
    project_setup

    run which mdl

    [ "${status}" == "0" ]
}
