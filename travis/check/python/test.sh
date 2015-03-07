#!/usr/bin/env bash
# /travis/check/python/test.sh
#
# Travis CI Script which tests a python project (also recording
# code coverage on the fly)
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

while getopts "m:" opt; do
    case "$opt" in
    m) module="$OPTARG"
       ;;
    esac
done

polysquare_task "Testing python project" \
    polysquare_note_failure_and_continue status \
        coverage run "--source=${module}" setup.py test
polysquare_exit_with_failure_on_script_failures
