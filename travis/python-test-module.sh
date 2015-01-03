#!/bin/bash
# /travis/python-test-module.sh
#
# Downloads scripts common to all polysquare python projects and run
# tests and linters. The MODULE environment variable must be set.
#
# See LICENCE.md for Copyright information

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

# Having python bytecode around is a waste of space and just inflates
# the build caches. Disable it.
export PYTHONDONTWRITEBYTECODE=1

wget public-travis-scripts.polysquare.org/prepare-lang-cache.sh > /dev/null 2>&1
wget public-travis-scripts.polysquare.org/python-lint.sh > /dev/null 2>&1
wget public-travis-scripts.polysquare.org/python-tests.sh > /dev/null 2>&1
wget public-travis-scripts.polysquare.org/project-lint.sh > /dev/null 2>&1

check_status_of bash project-lint.sh -d . -e py
check_status_of bash python-lint.sh -m "${MODULE}"
check_status_of bash python-tests.sh -m "${MODULE}"
check_status_of bash prepare-lang-cache.sh -l haskell -p ~/virtualenv
