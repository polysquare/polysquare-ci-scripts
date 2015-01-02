#!/usr/bin/env bash
# /travis/project-lint.sh
#
# Travis CI Script to lint project files
#
# See LICENCE.md for Copyright information

printf "\n=> Linting Project"


while getopts "d:e:x:" opt; do
    case "$opt" in
    d) directories+=" $OPTARG"
       ;;
    e) extensions+=" $OPTARG"
       ;;
    x) exclusions+=" $OPTARG"
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

function get_extensions_arguments() {
    local result=$1
    local cmd_append=""

    for extension in ${extensions} ; do
        cmd_append="${cmd_append} -name \"*.${extension}\""
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

# Put .cabal/bin in PATH so that pandoc is available when
# installing polysquare-generic-file-linter. If pypandoc
# is installed but pandoc isn't available, then the installer
# will error out.
export PATH=${HOME}/.cabal/bin:${PATH}

printf "\n   ... Installing requirements "
check_status_of gem install mdl
check_status_of pip install polysquare-generic-file-linter

printf "\n   ... Linting files for Polysquare style guide "
get_exclusions_arguments excl_args
get_extensions_arguments ext_args

for dir in ${directories} ; do
    cmd="find ${dir} -type f ${excl_args} ${ext_args}"
    files=$(eval "${cmd}")

    for file in ${files} ; do
        check_status_of polysquare-generic-file-linter "${file}"
    done
done

printf "\n   ... Linting Markdown documentation "
check_status_of mdl .

printf "\n"

exit ${failures}
