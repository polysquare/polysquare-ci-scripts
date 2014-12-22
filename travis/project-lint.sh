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

function print_exclusions {
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

echo "   ... Linting files"

for directory in ${directories} ; do
    for extension in ${extensions} ; do
        if [[ -z ${exclusions} ]] ; then
            print_exclusions | \
                xargs find "${directory}" -type f \
                    -name "*.${extension}" -print0 | \
                        xargs -0 -L 1 polysquare-generic-file-linter
        else
            find "${directory}" -type f -name "*.${extension}" -print0 | \
                xargs -0 -L 1 echo polysquare-generic-file-linter
        fi
    done
done

mdl .
