#!/usr/bin/env bats
# /tests/setup-python.bats
#
# Ensure that the linting and testing facilities made available to us in
# lint.sh and test.sh work correctly.
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

@test "Python build is installed in container" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/python_setup.sh" -d \
        "${CONTAINER_DIR}"

    [ -f "${CONTAINER_DIR}/_languages/python/python-build/bin/python-build" ]
}

@test "Can install python versions" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/python_setup.sh" -d \
        "${CONTAINER_DIR}" -v "3.4.2"

    [ -f "${CONTAINER_DIR}/_languages/python/3.4.2/bin/python" ]
}

@test "Python 3.4 installation has python3.4 lib directory" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/python_setup.sh" -d \
        "${CONTAINER_DIR}" -v "3.4.2"

    [ -d "${CONTAINER_DIR}/_languages/python/3.4.2/lib/python3.4" ]
}

@test "Python 2.7 installation has python2.7 lib directory" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/python_setup.sh" -d \
        "${CONTAINER_DIR}" -v "2.7"

    [ -d "${CONTAINER_DIR}/_languages/python/2.7/lib/python2.7" ]
}

@test "Python 2.7 installation can be activated and has correct verison" {
    bash "${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/python_setup.sh" -d \
        "${CONTAINER_DIR}" -v "2.7"

    PATH="${CONTAINER_DIR}/_languages/python/2.7/bin:${PATH}" \
        run python --version

    [[ "${output?}" =~ ^.*2.7.*$ ]]
}

@test "Python 3.4 installation can be activated and has correct verison" {
    bash "${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/python_setup.sh" -d \
        "${CONTAINER_DIR}" -v "2.7"

    PATH="${CONTAINER_DIR}/_languages/python/2.7/bin:${PATH}" \
        run python --version

    [[ "${output?}" =~ ^.*2.7.*$ ]]
}

