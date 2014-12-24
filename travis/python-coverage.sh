#!/usr/bin/env bash
# /travis/python-coverage.sh
#
# Travis CI Script to print and upload coverage report
#
# See LICENCE.md for Copyright information

echo "=> Reporting test coverage"

failures=0

function check_status_of() {
    concat_cmd=$(echo "$@" | xargs echo)
    eval "${concat_cmd}"
    if [[ $? != 0 ]] ; then
        failures=$((failures + 1))
    fi
}

check_status_of coverage report -m
check_status_of coveralls

exit ${failures}
