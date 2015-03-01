#!/usr/bin/env bash
# /tests/polysquare_container_copy_helper.bash
#
# Copies the contents of the existing CONTAINER_DIR to a temporary
# directory then deletes it later. Useful to speed up parts of tests.
#
# See LICENCE.md for Copyright information

setup() {
    local bootstrap="_scripts/bootstrap.sh"

    # Create a new CONTAINER_DIR as a copy of the current one and move
    # the old one out of the way. This ensures taht when scripts
    # invoke bootstrap.sh, they will only use executables in the
    # copy of CONTAINER_DIR's path
    local temporary_container_directory=$(mktemp -d /tmp/psq-container.XXXXXX)
    export ORIGINAL_CONTAINER_DIR="${CONTAINER_DIR}"
    export MOVED_CONTAINER_DIR="${CONTAINER_DIR%/}.moved"
    export CONTAINER_DIR="${temporary_container_directory}"
    export ORIGINAL_BOOTSTRAP="${__POLYSQUARE_CI_SCRIPTS_BOOTSTRAP}"
    export __POLYSQUARE_CI_SCRIPTS_BOOTSTRAP="${CONTAINER_DIR}/${bootstrap}"
    cp -TRf "${ORIGINAL_CONTAINER_DIR}" "${CONTAINER_DIR}"
    mv "${ORIGINAL_CONTAINER_DIR}" "${MOVED_CONTAINER_DIR}"
}

teardown() {
    __polysquare_delete_script_outputs
    rm -rf "${CONTAINER_DIR}"
    mv "${MOVED_CONTAINER_DIR}" "${ORIGINAL_CONTAINER_DIR}"
    export CONTAINER_DIR="${ORIGINAL_CONTAINER_DIR}"
    export __POLYSQUARE_CI_SCRIPTS_BOOTSTRAP="${ORIGINAL_BOOTSTRAP}"
    unset ORIGINAL_CONTAINER_DIR
    unset MOVED_CONTAINER_DIR
    unset ORIGINAL_BOOTSTRAP
}
