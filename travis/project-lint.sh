#!/usr/bin/env bash
# /travis/project-lint.sh
#
# Travis CI Script to lint project files
#
# See LICENCE.md for Copyright information

echo "=> Linting Files for Polysquare Style Guide"
echo "   ... Installing requirements"
gem install mdl > /dev/null 2>&1
pip install polysquare-generic-file-linter > /dev/null 2>&1

# Always exclude .git
exclusions="$(pwd)/.git"

while getopts "d:e:x:" opt; do
    case "$opt" in
    d) directories+=$OPTARG
       ;;
    e) extensions+=$OPTARG
       ;;
    x) exclusions+=$OPTARG
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

get_exclusions_arguments excl_args
get_extensions_arguments ext_args

echo "   ... Linting files for Polysquare style guide"

for dir in ${directories} ; do
    cmd="find ${dir} -type f ${excl_args} ${ext_args}"
    files=$(eval "${cmd}")

    for file in ${files} ; do
        polysquare-generic-file-linter "${file}"
    done
done

echo "   ... Linting Markdown documentation"

mdl .
