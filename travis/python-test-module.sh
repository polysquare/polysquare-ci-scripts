#!/bin/bash
# /travis/python-test-module.sh
#
# Downloads scripts common to all polysquare python projects and run
# tests and linters. The MODULE environment variable must be set.
#
# See LICENCE.md for Copyright information

failures=0

function check_status_of() {
    concat_cmd=$(echo "$@" | xargs echo)
    eval "${concat_cmd}"
    if [[ $? != 0 ]] ; then
        failures=$((failures + 1))
        printf "\nA subcommand failed. "
        printf "Consider deleting the travis build cache.\n"
    fi
}

# Having python bytecode around is a waste of space and just inflates
# the build caches. Disable it.
export PYTHONDONTWRITEBYTECODE=1

wget public-travis-scripts.polysquare.org/prepare-lang-cache.sh > /dev/null 2>&1
wget public-travis-scripts.polysquare.org/python-lint.sh > /dev/null 2>&1
wget public-travis-scripts.polysquare.org/python-tests.sh > /dev/null 2>&1
wget public-travis-scripts.polysquare.org/project-lint.sh > /dev/null 2>&1

check_status_of bash project-lint.sh -d . -e py
check_status_of bash python-lint.sh -m "${MODULE}"
check_status_of bash python-tests.sh -m "${MODULE}"
check_status_of bash prepare-lang-cache.sh -l haskell -p ~/virtualenv

exit ${failures}
