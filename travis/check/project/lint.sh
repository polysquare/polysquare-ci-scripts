#!/usr/bin/env bash
# /travis/check/project/lint.sh
#
# Travis CI Script which lints project and markdown files. Depends on having
# markdownlint and polysquare-generic-file-linter installed. Use
# setup/project/setup.sh to install them.
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

function polysquare_check_files_with {
    for file in ${*:2} ; do
        polysquare_report_failures_and_continue exit_status "$1" "${file}"
    done
}

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

function polysquare_check_files_for_style_guide {
    local excl
    local ext
    local cmd
    local lint_files

    polysquare_get_find_exclusions_arguments excl "${exclusions}"
    polysquare_get_find_extensions_arguments ext "${extensions}"

    for directory in ${directories} ; do
        cmd="find ${directory} -type f ${ext} ${excl}"
        lint_files+=$(eval "${cmd}")
        lint_files+=" "
    done

    polysquare_task "Linting files with polysquare style guide linter" \
        polysquare_check_files_with polysquare-generic-file-linter \
            "${lint_files}"
    polysquare_task "Linting markdown documentation" \
        polysquare_report_failures_and_continue exit_status mdl .
}

polysquare_task "Checking compliance with polysquare style guide" \
    polysquare_check_files_for_style_guide
polysquare_exit_with_failure_on_script_failures
