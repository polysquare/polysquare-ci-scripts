#!/usr/bin/env bash
# /travis/cmake-test-in-container.sh
#
# Travis CI Script to set up a distro container and test a CMake
# project inside of that container.
#
# See LICENCE.md for Copyright information

set -e

export CONTAINER_DISTRO=Ubuntu
export CONTAINER_RELEASE=precise

wget public-travis-scripts.polysquare.org/cmake-install.sh > /dev/null 2>&1
wget public-travis-scripts.polysquare.org/cmake-lint.sh > /dev/null 2>&1
wget public-travis-scripts.polysquare.org/project-lint.sh > /dev/null 2>&1
wget public-travis-scripts.polysquare.org/cmake-tests.sh > /dev/null 2>&1
wget public-travis-scripts.polysquare.org/prepare-lang-cache.sh > /dev/null 2>&1

function get_exclusions_arguments() {
    local result=$1
    local cmd_append=""

    for exclusion in ${EXCLUDE_FROM_LINT} ; do
        cmd_append="${cmd_append} -x ${exclusion}"
    done

    eval "${result}='${cmd_append}'"
}

get_exclusions_arguments lint_exclusions

# Sets up container for us to use later. This makes the
# psq-travis-container-exec command available for use.
bash cmake-install.sh -v "${CMAKE_VERSION}"
eval "bash cmake-lint.sh -n ${NAMESPACE} ${lint_exclusions?}"
eval "bash project-lint.sh -d . -e cmake -e txt ${lint_exclusions?}"

# Create a temporary wrapper script which forwards on to cmake-tests.sh
tests_wrapper=$(mktemp /tmp/tmp.XXXXXXX)
cat >"${tests_wrapper}" <<EOL
#!/bin/bash
set -e
bash cmake-tests.sh
EOL

psq-travis-container-exec "${CONTAINER_DIR}" --cmd bash "${tests_wrapper}"
eval "bash prepare-lang-cache.sh -p ${CONTAINER_DIR} -l python"
