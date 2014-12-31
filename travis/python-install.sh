#!/usr/bin/env bash
# /travis/python-install.sh
#
# Travis CI Script to run install a python project and its dependencies
#
# See LICENCE.md for Copyright information

failures=0

function check_status_of() {
    concat_cmd=$(echo "$@" | xargs echo)
    eval "${concat_cmd}"
    if [[ $? != 0 ]] ; then
        failures=$((failures + 1))
    fi
}

function setup_pandoc() {
    temporary_language_setup_directory=$(mktemp -d)
    pushd "${temporary_language_setup_directory}" > /dev/null 2>&1
    wget public-travis-scripts.polysquare.org/setup-lang.sh > /dev/null 2>&1

    # Not using check_status_of here since we need to pop the directory if
    # we need to get out for wget failure
    if [[ $? != 0 ]] ; then
        echo "ERROR: Failed to download setup-lang.sh"
        popd
        exit 1
    fi

    setup_languages_script="bash
    setup-lang.sh
    -p ~/virtualenv/haskell
    -l haskell
    "

    check_status_of "${setup_languages_script}"
    popd > /dev/null 2>&1

    echo "=> Installing pandoc"
    cabal install pandoc
}

setup_pandoc

echo "=> Installing python project and dependencies"

echo "   ... Installing doc converters (pypandoc, setuptools-markdown)"
pip install pandoc setuptools-markdown

echo "   ... Installing project"
check_status_of python setup.py install
check_status_of python setup.py clean --all
rm -rf build
rm -rf dist

echo "   ... Installing test dependencies"
check_status_of pip install -e ".[test]" --process-dependency-links

exit ${failures}
