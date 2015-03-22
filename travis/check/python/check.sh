#!/usr/bin/env bash
# /travis/check/python/check.sh
#
# Travis CI Script which supervises other scripts to check python files. It
# should be run normally with bash.
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

while getopts "x:d:m:" opt; do
    case "$opt" in
    x) exclusions+=" $OPTARG"
       ;;
    d) directories+=" $OPTARG"
       ;;
    m) module="$OPTARG"
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
    -e py
polysquare_note_failure_and_continue status bash \
    "${POLYSQUARE_CI_SCRIPTS_DIR}/check/python/lint.sh" \
    "${dir_switches?}" \
    "${excl_switches?}"
polysquare_note_failure_and_continue status bash \
    "${POLYSQUARE_CI_SCRIPTS_DIR}/check/python/test.sh" \
    -m "${module}"
polysquare_note_failure_and_continue status bash \
    "${POLYSQUARE_CHECK_SCRIPTS}/check/python/install.sh"

polysquare_note_failure_and_continue \
    polysquare_fetch_and_exec check/python/deploy.sh

polysquare_exit_with_failure_on_script_failures
