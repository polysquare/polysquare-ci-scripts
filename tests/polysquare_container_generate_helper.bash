#!/usr/bin/env bash
# /tests/polysquare_container_generate_helper.bash
#
# Generates a container in CONTAINER_DIR/test/${language} where language is 
# the first argument, using the function provided as the second argument using
# the function provided as the first argument.  The container is only generated
# if it does not exist and should be consistent between test runs. The
# container will then be set as CONTAINER_DIR (with the original container being
# set as _POLYSQUARE_GENERATE_LAST_CONTAINER) and the original
# container will be restored on teardown
#
# See LICENCE.md for Copyright information

function polysquare_generate_container_setup {
    local language="$1"
    local gen_func="$2"

    local test_container_dir="${HOME}/.container-dir-test/${language}"

    # Base of this container.
    if ! [ -d "${test_container_dir}" ] ; then
        mkdir -p "${HOME}/.container-dir-test"
        cp -TRf "${CONTAINER_DIR}" "${test_container_dir}"

        (eval "${gen_func} \"${test_container_dir}\" \"${language}\"") \
            2> /dev/null
    fi

    local -r temp_cont_dir_temp=$(mktemp -d "/tmp/container-swp.XXXXXX")
    rm -rf "${temp_cont_dir_temp}"
    mv "${CONTAINER_DIR}" "${temp_cont_dir_temp}"
    mv "${test_container_dir}" "${CONTAINER_DIR}"

    export _POLYSQUARE_GENERATE_LAST_CONTAINER="${temp_cont_dir_temp}"
    export _POLYSQUARE_GENERATE_TEST_CONTAINER="${test_container_dir}"
}

function polysquare_generate_container_teardown {
    mv "${CONTAINER_DIR}" "${_POLYSQUARE_GENERATE_TEST_CONTAINER}"
    mv "${_POLYSQUARE_GENERATE_LAST_CONTAINER}" "${CONTAINER_DIR}"
    unset _POLYSQUARE_GENERATE_CONTAINER_LAST_CONTAINER
    unset _POLYSQUARE_GENERATE_TEST_CONTAINER
}
