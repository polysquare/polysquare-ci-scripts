#!/usr/bin/env bash
# /travis/util.sh
#
# Travis CI Script which contains various utilities for
# other scripts. Since only functions are defined in here,
# it is possible to download it and eval it directly. For
# example:
#
#     eval $(curl -LSs public-travis-scripts.polysquare.org/util.sh | bash)
#
# See LICENCE.md for Copyright information

function polysquare_print_task {
    >&2 printf "\n=> %s" "$*"
}

function polysquare_print_status {
    >&2 printf "\n    ... %s" "$*"
}

function polysquare_print_error {
    >&2 printf "\n   !!! %s" "$*"
}

__polysquare_script_failures=0;
__polysquare_last_command_exit_status=0;
function polysquare_report_failures_and_continue {
    local output_file=$(mktemp /tmp/tmp.XXXXXXX)
    local concat_cmd=$(echo "$@" | xargs echo)
    eval "${concat_cmd}" > "${output_file}" 2>&1  &
    local command_pid=$!
    
    # This is effectively a tool to feed the travis-ci script
    # watchdog. Print a dot every sixty seconds.
    echo "while :; sleep 60; do printf '.'; done" | bash 2> /dev/null 1>&2 &
    local printer_pid=$!
    
    wait "${command_pid}"
    local result=$?
    kill "${printer_pid}"
    wait "${printer_pid}" 2> /dev/null
    if [[ $command_result != 0 ]] ; then
        printf "\n"
        >&2 cat "${output_file}"
        polysquare_print_error "Subcommand ${concat_cmd} failed with ${result}"
        polysquare_print_error "Consider deleting the travis build cache"
        __polysquare_script_failures=$((__polysquare_script_failures + 1))
        __polysquare_last_command_exit_status="${result}"
    fi
}

function polysquare_fatal_error_on_failure {
    # First call polysquare_report_failures_and_continue then
    # check if __polysquare_script_failures is greater than
    # 0. If it is, that means this script, or a series of subscripts,
    # have failed.
    polysquare_report_failures_and_continue "$@"

    if [ "${failures}" != 0 ] ; then
        exit "${__polysquare_last_command_exit_status}"
    fi
}

function polysquare_get_find_exclusions_arguments {
    local result=$1
    local cmd_append=""

    for exclusion in ${exclusions} ; do
        if [ -d "${exclusion}" ] ; then
            cmd_append="${cmd_append} -not -path \"${exclusion}/*\""
        else
            if [ -f "${exclusion}" ] ; then
                exclude_name=$(basename "${exclusion}")
                cmd_append="${cmd_append} -not -name \"*${exclude_name}\""
            fi
        fi
    done

    eval "${result}"="'${cmd_append}'"
}

function polysquare_get_find_extensions_arguments {
    local result=$1
    local cmd_append=""

    for extension in ${extensions} ; do
        cmd_append="${cmd_append} -name \"*.${extension}\""
    done

    eval "${result}"="'${cmd_append}'"
}

function polysquare_fetch {
    result=$1
    local url=$1
    local output_file="${CONTAINER_DIR}/_scripts/$(echo "${url}" | cut -d/ -f2)"

    if ! [ -f "${output_file}" ] ; then
        curl "${url}" --create-dirs -O "${output_file}"
    fi

    eval "${result}"="'${output_file}'"
}

function polysquare_fetch_and_source {
    local output_file=""
    polysquare_fetch output_file "$1"
    shift
    source "${output_file}" "$@"
}

function polysquare_fetch_and_run {
    local output_file=""
    polysquare_fetch output_file "$1"
    shift
    bash "${output_file}" "$@"
}
