#!/usr/bin/env bash
# /travis/cmake-install.sh
#
# Travis CI Script to install CMake from apt inside a container.
#
# See LICENCE.md for Copyright information

while getopts "v:" opt; do
    case "$opt" in
    v) version+="$OPTARG"
       ;;
    esac
done

failures=0

function check_status_of() {
    output_file=$(mktemp /tmp/tmp.XXXXXXX)
    concat_cmd=$(echo "$@" | xargs echo)
    eval "${concat_cmd}" > "${output_file}" 2>&1  &
    command_pid=$!
    
    # This is effectively a tool to feed the travis-ci script
    # watchdog. Print a dot every sixty seconds.
    echo "while :; sleep 60; do printf '.'; done" | bash 2> /dev/null &
    printer_pid=$!
    
    wait "${command_pid}"
    command_result=$?
    kill "${printer_pid}"
    wait "${printer_pid}" 2> /dev/null
    if [[ $command_result != 0 ]] ; then
        failures=$((failures + 1))
        cat "${output_file}"
        printf "\nA subcommand failed. "
        printf "Consider deleting the travis build cache.\n"
    fi
}

# Create the distro container. The following are packages and
# repositories we want in every container, no matter what CMake version
# we are looking for. This gets us access to ninja and lcov.
build_deps_repositories="{launchpad}/saiarcot895/chromium-dev/ubuntu {release} main
{ubuntu} {release} universe"

echo "${build_deps_repositories}" > REPOSITORIES.Ubuntu
echo "ninja-build build-essential lcov" > DEPENDENCIES.Ubuntu
wget public-travis-scripts.polysquare.org/distro-container.sh > /dev/null 2>&1

# Don't suppress output - we'll just check the exit status manually
bash distro-container.sh -p ~/container
if [[ $? != 0 ]] ; then
    exit 1
fi

cmake_repositories_contents="deb http://ppa.launchpad.net/smspillaz/cmake-${version} ${CONTAINER_RELEASE}/ubuntu main"

# Installation script, which we'll have the container execute for us.
script_file_contents="#!/bin/bash
set -e
echo \"${cmake_repositories_contents}\" >> /etc/apt/sources.list.d/cmake.list
apt-get update -y --force-yes
apt-get remove cmake -y --force-yes
apt-get install cmake  -y --force-yes
"

script_file=$(mktemp /tmp/tmp.XXXXXXX)
echo "${script_file_contents}" >> "${script_file}"

printf "\n=> Installing cmake (%s) into container" "${version}"
check_status_of psq-travis-container-exec ~/container --cmd bash "${script_file}"
printf "\n"

exit "${failures}"
