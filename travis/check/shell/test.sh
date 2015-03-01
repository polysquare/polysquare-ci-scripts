#!/usr/bin/env bash
# /travis/check/shell/test.sh
#
# Travis CI Script which runs bats on all found test files within the test/
# directory.
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

function polysquare_test_bash_files {
    cmd="polysquare_sorted_find tests -type f -name \"*.bats\""
    tests=$(eval "${cmd}")
    for test in ${tests} ; do
        polysquare_task "Running tests in ${test}" \
            polysquare_note_failure_and_continue status bats "${test}"
    done
}

polysquare_task "Testing bash files" polysquare_test_bash_files
polysquare_exit_with_failure_on_script_failures
