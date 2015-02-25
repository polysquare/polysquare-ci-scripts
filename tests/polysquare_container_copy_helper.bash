#!/usr/bin/env bash
# /tests/polysquare_ci_scripts_helper.bash
#
# Copies the contents of the existing CONTAINER_DIR to a temporary
# directory then deletes it later. Useful to speed up parts of tests.
#
# See LICENCE.md for Copyright information

export POLYSQUARE_TRAVIS_SCRIPTS="${BATS_TEST_DIRNAME}/../travis/"
export _POLYSQUARE_DONT_PRINT_DOTS=1
export POLYSQUARE_HOST="127.0.0.1:8080"

setup() {
    local temporary_container_directory=$(mktemp -d /tmp/psq-container.XXXXXX)
    export _CONTAINER_DIR="${CONTAINER_DIR}"
    export CONTAINER_DIR="${temporary_container_directory}"
    rsync -r -u -l "${_CONTAINER_DIR}" "${CONTAINER_DIR}"
}

teardown() {
    rm -rf "${CONTAINER_DIR}"
    export CONTAINER_DIR="${_CONTAINER_DIR}"
    unset _CONTAINER_DIR
}
