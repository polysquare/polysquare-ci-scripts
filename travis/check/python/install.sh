#!/usr/bin/env bash
# /travis/check/python/install.sh
#
# Travis CI Script which installs a python project (checking that the install
# succeeded without errors)
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

polysquare_task "Installing python project" \
    polysquare_note_failure_and_continue status \
        python setup.py install
polysquare_exit_with_failure_on_script_failures
