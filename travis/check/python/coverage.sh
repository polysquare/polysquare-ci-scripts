#!/usr/bin/env bash
# /travis/check/python/coverage.sh
#
# Travis CI Script which reports on coverage statistics for a python project
# and then uploads them to coveralls.
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

function polysuare_process_python_coverage_results {
    polysquare_task "Making coverage report" \
        polysquare_note_failure_and_continue status \
            coverage report -m

    if [ -z "${_POLYSQUARE_TESTING_WITH_BATS}" ] ; then
        polysquare_task "Uploading coverage report" \
            polysquare_note_failure_and_continue status coveralls
    fi
}

polysquare_task "Processing coverage results" \
    polysquare_note_failure_and_continue status \
        polysuare_process_python_coverage_results
polysquare_exit_with_failure_on_script_failures
