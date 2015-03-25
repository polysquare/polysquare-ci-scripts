#!/usr/bin/env bash
# /travis/check/shell/check.sh
#
# Travis CI Script which supervises other scripts to check shell files. It
# should be run normally with bash.
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

while getopts "x:d:" opt; do
    case "$opt" in
    x) exclusions+=" $OPTARG"
       ;;
    d) directories+=" $OPTARG"
       ;;
    esac
done

polysquare_repeat_switch_for_list excl_switches "-x" "${exclusions}"
polysquare_repeat_switch_for_list dir_switches "-d" "${directories}"

export POLYSQUARE_CHECK_SCRIPTS="${POLYSQUARE_CI_SCRIPTS_DIR}/check"

polysquare_note_failure_and_continue status bash \
    "${POLYSQUARE_CI_SCRIPTS_DIR}/check/project/check.sh" \
    "${excl_switches?}" \
    "${dir_switches?}" \
    -e sh \
    -e bash \
    -e bats
polysquare_note_failure_and_continue status bash \
    "${POLYSQUARE_CI_SCRIPTS_DIR}/check/shell/lint.sh" \
    "${excl_switches?}" \
    "${dir_switches?}"
polysquare_note_failure_and_continue status bashcov bash \
    "${POLYSQUARE_CI_SCRIPTS_DIR}/check/shell/test.sh"

polysquare_exit_with_failure_on_script_failures
