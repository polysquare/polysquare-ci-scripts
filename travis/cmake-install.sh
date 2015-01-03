#!/usr/bin/env bash
# /travis/cmake-install.sh
#
# Travis CI Script to install CMake from apt inside a container.
#
# See LICENCE.md for Copyright information

echo "=> Installing CMake inside container " \
    "${CONTAINER_DISTRO} ${CONTAINER_RELEASE}"
while getopts "v:" opt; do
    case "$opt" in
    v) version+=" $OPTARG"
       ;;
    esac
done

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

repositories_contents="{launchpad}/smspillaz/cmake-${version} main"
packages_contents="ninja-build cmake lcov"

echo "${repositories_contents}" > "REPOSITORIES.${CONTAINER_DISTRO}"
echo "${packages_contents}" > "DEPENDENCIES.${CONTAINER_DISTRO}"

wget public-travis-scripts.polysquare.org/distro-container.sh
check_status_of bash distro-container.sh

exit "${failures}"
