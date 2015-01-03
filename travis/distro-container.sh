#!/bin/bash
# /travis/distro-container.sh
#
# Shell script to create a "distribution container". The container can
# be controlled with the following environment variables:
# - CONTAINER_DISTRO: Distribution to use
# - CONTAINER_RELEASE: Distribution release
# - CONTAINER_ARCH: Distribution architecture (defaults to current arch)
#
# Dependencies can be installed in the container by providing a
# DEPENDENCIES.{Distro} and repositories can be added by providing a
# REPOSITORIES.{Distro}. Distro will by replaced by the name of the distribution
# to use.
#
# Certain keywords are automatically replaced in the REPOSITORIES file. Those
# are:
# - ubuntu: http://archive.ubuntu.com/ubuntu
# - release: The value of CONTAINER_RELEASE
# - debian: http://ftp.debian.org
# - launchpad: http://ppa.launchpad.com/ppa
#
# See LICENCE.md for Copyright information

function check_status_of() {
    local concat_cmd=$(echo "$@" | xargs echo)
    eval "${concat_cmd}"
    local result=$?
    if [[ $result != 0 ]] ; then
        exit ${result}
    fi
}

function output_on_failure() {
    local output_file=$(mktemp /tmp/tmp.XXXXXXX)
    local concat_cmd=$(echo "$@" | xargs echo)
    eval "${concat_cmd}" > "${output_file}" 2>&1
    local result=$?
    if [[ $result != 0 ]] ; then
        cat "${output_file}"
        exit ${result}
    fi
}

function setup_container() {
    echo "=> Setting up container ${CONTAINER_DISTRO} ${CONTAINER_RELEASE}"\
        "${CONTAINER_ARCH}"

    local path=$1
    echo "   ... Installing polysquare-travis-container"
    output_on_failure pip install https://github.com/polysquare/polysquare-travis-container/tarball/master#egg=polysquare-travis-container-0.0.1 --process-dependency-links
    echo "   ... Creating container"
    echo ""

    create_cmd="
psq-travis-container-create
${path}
"

    if [ -e "$(pwd)/DEPENDENCIES.${CONTAINER_DISTRO}" ] ; then
        create_cmd+=" --packages $(pwd)/DEPENDENCIES.${CONTAINER_DISTRO}"
    fi

    if [ -e "$(pwd)/REPOSITORIES.${CONTAINER_DISTRO}" ] ; then
        create_cmd+=" --repositories $(pwd)/REPOSITORIES.${CONTAINER_DISTRO}"
    fi
    check_status_of "${create_cmd}"
}

setup_container ~/contianer
