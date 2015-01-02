#!/usr/bin/env bash
# /travis/shell-lint.sh
#
# Travis CI Script to lint bash files
#
# See LICENCE.md for Copyright information

echo "=> Linting Shell Files"

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
    eval "${concat_cmd}" > "${output_file}" 2>&1
    if [[ $? != 0 ]] ; then
        failures=$((failures + 1))
        cat "${output_file}"
        echo "A subcommand failed. Consider deleting the travis build cache."
    fi
}

echo "   ... Installing requirements"
check_status_of cabal install shellcheck
check_status_of pip install bashlint

echo "   ... Linting files"
get_exclusions_arguments excl_args
for directory in ${directories} ; do
    cmd="find ${directory} -type f -name \"*.sh\" ${excl_args}"
    shell_files=$(eval "${cmd}")

    for file in ${shell_files} ; do
        check_status_of shellcheck "${file}"
        check_status_of bashlint "${file}"
    done
done

exit ${failures}
