#!/usr/bin/env bats
# /tests/util-fetch.bats
#
# Tests for the utility functions to fetch shell scripts in travis/
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/util.sh"

setup() {
    server_dir=$(mktemp -d /tmp/psq-container.XXXXXX)
    export server_dir
    mkdir -p "${server_dir}" > /dev/null 2>&1
    pushd "${server_dir}" > /dev/null 2>&1
    touch "fetch-local-test.sh"
    python -m "SimpleHTTPServer" 8080 > /dev/null 2>&1 &
    sleep 1 # Allow SimpleHTTPServer to start up
    export __polysquare_fake_host_pid=$!
    popd > /dev/null 2>&1

    POLYSQUARE_CI_SCRIPTS_DIR=$(mktemp -d /tmp/psq-container.XXXXXX)
    export POLYSQUARE_CI_SCRIPTS_DIR

    mkdir -p "${POLYSQUARE_CI_SCRIPTS_DIR}" > /dev/null 2>&1
}

teardown() {
    kill "${__polysquare_fake_host_pid}"
    rm -rf "${server_dir}" "${POLYSQUARE_CI_SCRIPTS_DIR}" > /dev/null 2>&1
}

@test "Fetch local file and get path in return value" {
    local expected_path="${POLYSQUARE_CI_SCRIPTS_DIR}/fetch-local-test.sh"

    polysquare_fetch_and_get_local_file local_path "fetch-local-test.sh"

    [ "${expected_path}" = "${local_path?}" ]
}

@test "Fetch local file and source it" {
    local server_side_file="${server_dir}/fetch-local-test.sh"
    echo "server_side_file_variable=1" > "${server_side_file}"
    polysquare_fetch_and_source "fetch-local-test.sh"

    [ "${server_side_file_variable?}" = "1" ]
}

@test "Fetch local file and source it with arguments" {
    local server_side_file="${server_dir}/fetch-local-test.sh"
    echo "server_side_file_variable=\$1" > "${server_side_file}"
    polysquare_fetch_and_source "fetch-local-test.sh" "argument"

    [ "${server_side_file_variable?}" = "argument" ]
}

@test "Fetch local file and evaluate its output upon running it" {
    local server_side_file="${server_dir}/fetch-local-test.sh"
    echo "echo \"server_side_file_variable=1\"" > "${server_side_file}"
    polysquare_fetch_and_eval "fetch-local-test.sh"

    [ "${server_side_file_variable?}" = "1" ]
}

@test "Fetch local file and evaluate its output upon running it with args" {
    local server_side_file="${server_dir}/fetch-local-test.sh"
    echo "echo \"server_side_file_variable=\$1\"" > "${server_side_file}"
    polysquare_fetch_and_eval "fetch-local-test.sh" "argument"

    [ "${server_side_file_variable?}" = "argument" ]
}

@test "Fetch local file and 'forward' its output" {
    local server_side_file="${server_dir}/fetch-local-test.sh"
    echo "echo server_side_file_variable=1" > "${server_side_file}"
    output=$(polysquare_fetch_and_fwd "fetch-local-test.sh")

    [ "${output?}" = "server_side_file_variable=1" ]
}

@test "Fetch local file and execute it - don't propagate variables" {
    local server_side_file="${server_dir}/fetch-local-test.sh"
    echo "echo server_side_file_variable=1" > "${server_side_file}"
    polysquare_fetch_and_exec "fetch-local-test.sh"

    [ "${server_side_file_variable?}" != "1" ]
}
