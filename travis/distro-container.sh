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

while getopts "p:l:" opt; do
    case "$opt" in
    p) path=$OPTARG
       ;;
    l) other_languages+=" $OPTARG"
       ;;
    esac
done

failures=0

function check_status_of() {
    concat_cmd=$(echo "$@" | xargs echo)
    eval "${concat_cmd}"
    result=$?
    if [[ $result != 0 ]] ; then
        exit ${result}
    fi
}

function setup_python() {
    path=$1
    other_languages=$2
    # Download setup-lang.sh into a temporary directory and set up
    # all local languages, with python set at version 3.3
    temporary_language_setup_directory=$(mktemp -d)
    pushd "${temporary_language_setup_directory}" > /dev/null 2>&1
    wget public-travis-scripts.polysquare.org/setup-lang.sh "$(pwd)" > /dev/null 2>&1
    
    # Not using check_status_of here since we need to pop the directory if
    # we need to get out for wget failure
    if [[ $? != 0 ]] ; then
        echo "ERROR: Failed to download setup-lang.sh"
        popd
        exit 1
    fi

    setup_languages_script="bash
    setup-lang.sh
    -p ${path}/languages_root
    -l python
    -s 3.3
    "

    for language in ${other_languages} ; do
        setup_languages_script+=" -l ${language}"
    done
    check_status_of "${setup_languages_script}"
    popd > /dev/null 2>&1
}

function setup_container() {
    echo "=> Setting up container ${CONTAINER_DISTRO} ${CONTAINER_RELEASE}"\
        "${CONTAINER_ARCH}"

    path=$1
    echo "   ... Installing polysquare-travis-container"
    pip install https://github.com/polysquare/polysquare-travis-container/tarball/master#egg=polysquare-travis-container-0.0.1 > /dev/null 2>&1

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

setup_python "${path}" "${other_languages}"
setup_container "${path}"

exit ${failures}
