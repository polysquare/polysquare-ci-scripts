#!/usr/bin/env bash
# /python-lint.sh
#
# Travis CI Script to lint python files
#
# See LICENCE.md for Copyright information

echo "=> Linting Shell Files"
echo "   ... Installing requirements"
cabal install shellcheck > /dev/null 2>&1

while getopts "d:x:" opt; do
    case "$opt" in
    x) exclusions+=$OPTARG
       ;;
    d) directories+=$OPTARG
       ;;
    esac
done

echo "   ... Linting files"

function print_exclusions() {
    for exclusion in ${exclusions} ; do
        if [ -d "${exclusion}" ] ; then
            echo "-not -path \"${exclusion}/*\""
        else
            if [ -f "${exclusion}" ] ; then
                echo "-not -name \"*${exclusion}\""
            fi
        fi
    done
}

for directory in ${directories} ; do
    if [[ -z $exclusions ]] ; then
        print_exclusions | \
            xargs find "${directory}" -type f -name "*.sh" -print0 | \
                xargs -0 -L 1 shellcheck
    else
        xargs find "${directory}" -type f -name "*.sh" -print0 | \
            xargs -0 -L 1 shellcheck
    fi
done
