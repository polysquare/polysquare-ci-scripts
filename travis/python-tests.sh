#!/usr/bin/env bash
# /travis/python-tests.sh
#
# Travis CI Script to run tests and count coverage
#
# See LICENCE.md for Copyright information

echo "=> Running tests and counting coverage"
while getopts "m:" opt; do
    case "$opt" in
    m) module=$OPTARG
       ;;
    esac
done

echo "   ... Installing coverage tools"
pip install \
    coverage \
    coveralls > /dev/null 2>&1

echo "   ... Running tests"

failures=0

function check_status_of() {
    concat_cmd=$(echo "$@" | xargs echo)
    eval "${concat_cmd}"
    if [[ $? != 0 ]] ; then
        failures=$((failures + 1))
    fi
}

check_status_of coverage run "--source=${module}" setup.py test

exit ${failures}
