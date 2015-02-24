#!/usr/bin/env bash
# /travis/check/shell/lint.sh
#
# Travis CI Script which lints bash files, depends on having shellcheck
# and bashlint installed. Use setup/shell/setup.sh to install them.
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

function polysquare_check_files_with {
    for file in ${*:2} ; do
        polysquare_report_failures_and_continue exit_status "$1" "${file}"
    done
}

while getopts "x:d:" opt; do
    case "$opt" in
    x) exclusions+=" $OPTARG"
       ;;
    d) directories+=" $OPTARG"
       ;;
    esac
done

function polysquare_check_shell_files {
    polysquare_get_find_exclusions_arguments excl "${exclusions}"
    polysquare_get_find_extensions_arguments ext "sh bats"

    for directory in ${directories} ; do
        cmd="find ${directory} -type f ${ext} ${excl}"
        shell_files+=$(eval "${cmd}")
    done

    polysquare_task "Linting shell files with shellcheck" \
        polysquare_check_files_with shellcheck "${shell_files}"
    polysquare_task "Linting shell files with bashlint" \
        polysquare_check_files_with bashlint "${shell_files}"
}

polysquare_exit_with_failure_on_script_failures
