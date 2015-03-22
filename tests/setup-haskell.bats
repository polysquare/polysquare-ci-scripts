#!/usr/bin/env bats
# /tests/setup-haskell.bats
#
# Ensure that we're able to set up a self-contained haskell installation
# correctly.
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

@test "hsenv is installed in container" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/haskell_setup.sh" -d \
        "${CONTAINER_DIR}"

    [ -f "${CONTAINER_DIR}/_languages/haskell/haskell-build/bin/hsenv" ]
}

@test "Can install GHC versions" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/haskell_setup.sh" -d \
        "${CONTAINER_DIR}" -v "7.8.4"

    [ -f "${CONTAINER_DIR}/_languages/haskell/.hsenv_7.8.4/ghc/bin/ghc" ]
}

@test "GHC 7.8.4 installation can be activated and has correct verison" {
    bash "${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/haskell_setup.sh" -d \
        "${CONTAINER_DIR}" -v "7.8.4"

    PATH="${CONTAINER_DIR}/_languages/haskell/.hsenv_7.8.4/ghc/bin:${PATH}" \
        run ghc --version

    [[ "${output?}" =~ ^.*7.8.4.*$ ]]
}

