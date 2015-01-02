#!/usr/bin/env bash
# /travis/shell-lint.sh
#
# Travis CI Script to lint bash files
#
# See LICENCE.md for Copyright information

printf "\n=> Linting Shell Files"

while getopts "d:x:" opt; do
    case "$opt" in
    x) exclusions+=" $OPTARG"
       ;;
    d) directories+=" $OPTARG"
       ;;
    esac
done

function get_exclusions_arguments() {
    local result=$1
    local cmd_append=""

    for exclusion in ${exclusions} ; do
        if [ -d "${exclusion}" ] ; then
            cmd_append="${cmd_append} -not -path \"${exclusion}/*\""
        else
            if [ -f "${exclusion}" ] ; then
                cmd_append="${cmd_append} -not -name \"*${exclusion}\""
            fi
        fi
    done

    eval "${result}"="'${cmd_append}'"
}

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

printf "\n   ... Installing requirements "
check_status_of cabal install shellcheck
check_status_of pip install bashlint

printf "\n   ... Linting files "
get_exclusions_arguments excl_args
for directory in ${directories} ; do
    cmd="find ${directory} -type f -name \"*.sh\" ${excl_args}"
    shell_files=$(eval "${cmd}")

    for file in ${shell_files} ; do
        check_status_of shellcheck "${file}"
        check_status_of bashlint "${file}"
    done
done

printf "\n"

exit ${failures}
