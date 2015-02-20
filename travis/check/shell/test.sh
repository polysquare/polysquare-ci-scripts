#!/usr/bin/env bash
# /travis/check/shell/test.sh
#
# Travis CI Script which runs bats on all found test files within the test/
# directory.
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

polysquare_print_task "Testing bash files"

cmd="find tests -type f -name \"*.bats\""
tests=$(eval "${cmd}")
for test in ${tests} ; do
    polysquare_print_status "Running tests in ${test}"
    printf "\n"
    polysquare_note_failure_and_continue status bats "${test}"
done

polysquare_task_completed

polysquare_exit_with_failure_on_script_failures
