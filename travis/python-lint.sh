#!/usr/bin/env bash
# /python-lint.sh
#
# Travis CI Script to lint python files
#
# See LICENCE.md for Copyright information

echo "=> Linting Python Files"
while getopts "m:" opt; do
    case "$opt" in
    m) module=$OPTARG
       ;;
    esac
done

pip install flake8 pep8-naming pylint > /dev/null 2>&1

if [[ $TRAVIS_PYTHON_VERSION == 2.7 || $PYTHON_SETUP_LOCALLY == 1 ]] ; then
    pip install pychecker > /dev/null 2>&1
fi

flake8 "${module}/" tests/ setup.py
pylint -f colorized "${module}" setup.py
if which pychecker ; then
    pychecker tests/*.py "${module}/*.py" setup.py
fi
