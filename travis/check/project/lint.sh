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
    polysquare_print_status "Linting files with $1"
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

polysquare_get_find_exclusions_arguments excl "${exclusions}"
polysquare_get_find_extensions_arguments ext "${extensions}"

for directory in ${directories} ; do
    cmd="find ${directory} -type f ${ext} ${excl}"
    lint_files+=$(eval "${cmd}")
done

polysquare_print_task \
    "Checking for compliance with polysquare project style guide"

polysquare_check_files_with polysquare-generic-file-linter "${lint_files}"

polysquare_print_status "Linting markdown documentation"
polysquare_report_failures_and_continue exit_status mdl .

polysquare_task_completed

polysquare_exit_with_failure_on_script_failures
