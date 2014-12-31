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

echo "   ... Installing documentation converters (pandoc, setuptools-markdown)"
pip install pandoc setuptools-markdown > /dev/null 2>&1

echo "   ... Installing project"
check_status_of python setup.py install
check_status_of python setup.py clean --all
rm -rf build
rm -rf dist

echo "   ... Installing test dependencies"
check_status_of pip install -e ".[test]" --process-dependency-links

exit ${failures}
