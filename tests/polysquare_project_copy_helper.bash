#!/usr/bin/env bash
# /tests/polysquare_project_copy_helper.bash
#
# Takes a copy of the sample project as indicated by the first arugment
#
# See LICENCE.md for Copyright information

function polysquare_project_copy_setup {
    local lang="$1"
    local cont="${CONTAINER_DIR}"
    local bootstrap="${BATS_TEST_DIRNAME}/../travis/bootstrap.sh"
    local project_language_base="${BATS_TEST_DIRNAME}/../sample/${lang}"
    local -r sample_project_copy="$(mktemp -d /tmp/psq-project.XXXXXX)"
    local boot

    cp -TRf "${project_language_base}" "${sample_project_copy}"
    export _POLYSQUARE_TEST_PROJECT="${sample_project_copy}"

    cd "${_POLYSQUARE_TEST_PROJECT}"

    boot=$(bash "${bootstrap}" -d "${cont}" -s "setup/${lang}/setup.sh")
    eval "${boot}"
}

function polysquare_project_copy_teardown {
    rm -rf "${_POLYSQUARE_TEST_PROJECT}"
}

function polysquare_setup_and_teardown_example_project {
    local _SETUP_AND_TEARDOWN_LAST_CONTAINER="${CONTAINER_DIR}"
    export CONTAINER_DIR="$1"
    polysquare_project_copy_setup "$2"
    polysquare_project_copy_teardown
    export CONTAINER_DIR="${_SETUP_AND_TEARDOWN_LAST_CONTAINER}"
}
