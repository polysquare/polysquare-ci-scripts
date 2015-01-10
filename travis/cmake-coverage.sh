#!/usr/bin/env bash
# /travis/cmake-coverage.sh
#
# Travis CI Script to upload coverage information for CMake files to
# coveralls.
#
# See LICENCE.md for Copyright information

printf "\n=> Reporting test coverage"

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

tracefile="${PWD}/tests/build/coverage.trace"

cmake_trace_to_lcov_cmd="
cmake
-DTRACEFILE=${tracefile}
-DLCOV_OUTPUT=${PWD}/tests/build/coverage.info
-P CMakeTraceToLCov.cmake"

if [ -f "${tracefile}" ] ; then
    check_status_of gem install coveralls-lcov
    check_status_of "${cmake_trace_to_lcov_cmd}"
    coveralls-lcov "tests/build/coverage.info"
else
    printf "\n... Tracefile does not exist, not running coverage step"
fi

exit "${failures}"
