#!/usr/bin/env bash
# /travis/check/shell/test.sh
#
# Travis CI Script which runs bats on all found test files within the test/
# directory.
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

polysquare_print_task "Testing bash files $(pwd)"

tests=$(find tests -type f -name \".bats\")
for test in ${tests} ; do
    polysquare_print_status "Running tests in ${test}"
done
