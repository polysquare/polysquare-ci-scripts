#!/usr/bin/env bash
# /travis/python-install.sh
#
# Travis CI Script to run install a python project and its dependencies
#
# See LICENCE.md for Copyright information

echo "=> Installing python project and dependencies"

failures=0

function check_status_of() {
    concat_cmd=$(echo "$@" | xargs echo)
    eval "${concat_cmd}"
    if [[ $? != 0 ]] ; then
        failures=$((failures + 1))
    fi
}

echo "   ... Installing project"
check_status_of python setup.py install

echo "   ... Installing test dependencies"
check_status_of pip install -e ".[test]"

exit ${failures}
