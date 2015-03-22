#!/usr/bin/env bash
# /tests/polysquare_ci_scripts_helper.bash
#
# Loader script for bats which sets the POLYSQUARE_TRAVIS_SCRIPTS
# environment variable for use with tests.
#
# See LICENCE.md for Copyright information

function polysquare_ci_scripts_helper_exports {
    travis_scripts="${BATS_TEST_DIRNAME}/../travis"
    POLYSQUARE_TRAVIS_SCRIPTS=$(cd "${travis_scripts}"; pwd)

    export POLYSQUARE_TRAVIS_SCRIPTS
    export _POLYSQUARE_DONT_PRINT_DOTS=1
    export _POLYSQUARE_TESTING_WITH_BATS=1
    export POLYSQUARE_HOST="127.0.0.1:8080"
}

function print_returned_args_on_newlines {
    local function_name="$1"
    local n_args="$2"

    local arguments_to_pass=${*:3}
    local arguments_to_check=(${*:3:$n_args})

    eval "${function_name} ${arguments_to_pass}" > /dev/null 2>&1

    for index in "${!arguments_to_check[@]}" ; do
        local argument_name="${arguments_to_check[$index]}"
        eval "local argument_value=\$$argument_name"
        echo "${argument_value?}"
    done
}

polysquare_ci_scripts_helper_exports
