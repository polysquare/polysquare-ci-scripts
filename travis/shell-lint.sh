#!/usr/bin/env bash
# /travis/shell-lint.sh
#
# Travis CI Script to lint bash files
#
# See LICENCE.md for Copyright information

echo "=> Linting Shell Files"
echo "   ... Installing requirements"
cabal install shellcheck > /dev/null 2>&1
pip install bashlint > /dev/null 2>&1

# Always exclude .git
exclusions="$(pwd)/.git"

while getopts "d:x:" opt; do
    case "$opt" in
    x) exclusions+=$OPTARG
       ;;
    d) directories+=$OPTARG
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

get_exclusions_arguments excl_args

echo "   ... Linting files"

for directory in ${directories} ; do
    cmd="find ${directory} -type f -name \"*.sh\" ${excl_args}"
    shell_files=$(eval "${cmd}")

    for file in ${shell_files} ; do
        shellcheck "${file}"
        bashlint "${file}"
    done
done
