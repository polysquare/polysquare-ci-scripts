#!/usr/bin/env bash
# /travis/check/project/check.sh
#
# Travis CI Script which supervises other scripts to check the project
# configuration generally. It should be run normally with bash.
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

while getopts "x:e:d:" opt; do
    case "$opt" in
    x) exclusions+=" $OPTARG"
       ;;
    e) extensions+=" $OPTARG"
       ;;
    d) directories+=" $OPTARG"
       ;;
    esac
done

polysquare_repeat_switch_for_list excl_switches "-x" "${exclusions}"
polysquare_repeat_switch_for_list ext_switches "-e" "${extensions}"
polysquare_repeat_switch_for_list dir_switches "-d" "${directories}"

polysquare_note_failure_and_continue status bash \
    "${POLYSQUARE_CI_SCRIPTS_DIR}/check/project/lint.sh" \
    "$excl_switches" \
    "$ext_switches" \
    "$dir_switches"

polysquare_exit_with_failure_on_script_failures
