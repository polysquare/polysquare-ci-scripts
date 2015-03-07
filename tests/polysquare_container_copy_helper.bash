#!/usr/bin/env bash
# /tests/polysquare_container_copy_helper.bash
#
# Copies the contents of the existing CONTAINER_DIR to a temporary
# directory then deletes it later. Useful to speed up parts of tests.
#
# See LICENCE.md for Copyright information

function polysquare_container_copy_setup {
    # Create a new CONTAINER_DIR as a copy of the current one and move
    # the old one out of the way. This ensures taht when scripts
    # invoke bootstrap.sh, they will only use executables in the
    # copy of CONTAINER_DIR's path
    local temporary_container_directory=$(mktemp -d "${HOME}/.psq-cont.XXXXXX")

    # Move the container directory on top of temporary_container_directory
    # and then copy it back in place.
    #
    # This will ensure that that the tests are only modifying their own
    # copy of the container directory. The container directory must
    # always stay in the same place since the language installations often
    # have hardcoded references to it.
    rm -rf "${temporary_container_directory}"
    mv "${CONTAINER_DIR}" "${temporary_container_directory}"

    export _POLYSQUARE_COPY_LAST_CONTAINER="${temporary_container_directory}"

    cp -rf "${temporary_container_directory}" "${CONTAINER_DIR}"
}

function polysquare_container_copy_teardown {
    __polysquare_delete_script_outputs
    rm -rf "${CONTAINER_DIR}"
    mv "${_POLYSQUARE_COPY_LAST_CONTAINER}" "${CONTAINER_DIR}"
    unset _POLYSQUARE_COPY_LAST_CONTAINER
}
