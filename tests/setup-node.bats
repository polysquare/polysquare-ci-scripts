#!/usr/bin/env bats
# /tests/setup-node.bats
#
# Test setting up a self-contained node installation
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
load polysquare_fresh_container_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/util.sh"

setup() {
    polysquare_fresh_container_setup
}

teardown() {
    polysquare_fresh_container_teardown
}

@test "nodeenv is installed in container" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/node_setup.sh" -d \
        "${CONTAINER_DIR}"

    [ -f "${CONTAINER_DIR}/_languages/node/nodeenv/bin/nodeenv" ]
}

@test "Can install node versions" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/node_setup.sh" -d \
        "${CONTAINER_DIR}" -v "0.12.0"

    [ -f "${CONTAINER_DIR}/_languages/node/0.12.0/bin/node" ]
}

@test "Node 0.12.0 installation can be activated and has correct verison" {
    local setup="${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/node_setup.sh"
    local -r script=$(bash "${setup}" -d "${CONTAINER_DIR}" -v 0.12.0)
    echo "${script}"
    eval "${script}"

    which npm
    which node
    
    run node --version
    [[ "${output?}" =~ ^.*0.12.0.*$ ]]
}

@test "Node 0.11.0 installation can be activated and has correct verison" {
    local setup="${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/node_setup.sh"
    local -r script=$(bash "${setup}" -d "${CONTAINER_DIR}" -v 0.11.0)
    eval "${script}"

    which npm
    which node
    
    run node --version
    [[ "${output?}" =~ ^.*0.11.0.*$ ]]
}

