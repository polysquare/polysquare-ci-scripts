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

export POLYSQUARE_HOST="${POLYSQUARE_HOST-public-travis-scripts.polysquare.org}"
export POLYSQUARE_SETUP_SCRIPTS="${POLYSQUARE_HOST}/setup";
export POLYSQUARE_CHECK_SCRIPTS="${POLYSQUARE_HOST}/check";

function polysquare_print_task {
    >&2 printf "\n=> %s" "$*"
}

function polysquare_print_status {
    >&2 printf "\n   ... %s" "$*"
}

function polysquare_print_error {
    >&2 printf "\n   !!! %s" "$*"
}

function polysquare_task_completed {
    >&2 printf "\n"
}

__polysquare_script_output_files=()
function __polysquare_delete_script_outputs {
    for output_file in "${__polysquare_script_output_files[@]}" ; do
        rm -rf "${output_file}"
    done
}

function _polysquare_monitor_command_internal_prologue {
    local printer_pid_return="$1"

    # This is effectively a tool to feed the travis-ci script
    # watchdog. Print a dot every sixty seconds.
    if [ -z "${_POLYSQUARE_DONT_PRINT_DOTS}" ] ; then
        echo "while :; sleep 60; do printf '.'; done" | bash 2> /dev/null 1>&2 &
        local printer_pid=$!
    else
        local printer_pid=0
    fi

    eval "${printer_pid_return}='${printer_pid}'"
}

function _polysquare_monitor_command_internal_epilogue {
    local printer_pid="$1"

    if [ -z "${_POLYSQUARE_DONT_PRINT_DOTS}" ] ; then
        kill -9 "${printer_pid}" > /dev/null 2>&1
    fi
}

function polysquare_monitor_command_status {
    local script_status_return="$1"
    local concat_cmd=$(echo "${*:2}" | xargs echo)

    _polysquare_monitor_command_internal_prologue printer_pid
    eval "${concat_cmd} 2>&1"

    local result=$?

    _polysquare_monitor_command_internal_epilogue "${printer_pid}"

    eval "${script_status_return}='${result}'"
}

function polysquare_monitor_command_output {
    local script_status_return="$1"
    local script_output_return="$2"
    local concat_cmd=$(echo "${*:3}" | xargs echo)
    local output_file="$(mktemp -t psq-util-sh.XXXXXX)"
    __polysquare_script_output_files+=("${output}")

    _polysquare_monitor_command_internal_prologue printer_pid concat_cmd
    eval "${concat_cmd} > ${output_file} 2>&1"

    local result=$?

    _polysquare_monitor_command_internal_epilogue "${printer_pid}"

    eval "${script_status_return}='${result}'"
    eval "${script_output_return}='${output_file}'"
}

__polysquare_script_failures=0;
function polysquare_note_failure_and_continue {
    local status_return="$1"
    local concat_cmd=$(echo "${*:2}" | xargs echo)
    polysquare_monitor_command_status status "${concat_cmd}"
    if [[ $status != 0 ]] ; then
        __polysquare_script_failures=$((__polysquare_script_failures + 1))
    fi

    eval "${status_return}='${status}'"
}

function polysquare_report_failures_and_continue {
    local status_return="$1"
    local concat_cmd=$(echo "${*:2}" | xargs echo)
    polysquare_monitor_command_output status output "${concat_cmd}"
    if [[ $status != 0 ]] ; then
        printf "\n"
        >&2 cat "${output}"
        __polysquare_script_failures=$((__polysquare_script_failures + 1))
        polysquare_print_error "Subcommand ${concat_cmd} failed with ${status}"
        polysquare_print_error "Consider deleting the travis build cache"
    fi

    eval "${status_return}='${status}'"
}

function polysquare_fatal_error_on_failure {
    # First call polysquare_report_failures_and_continue then
    # check if exit_status is greater than 0. If it is, that means this script
    # or a series of subscripts, have failed.
    polysquare_report_failures_and_continue exit_status "$@"

    if [[ $exit_status != 0 ]] ; then
        exit "${exit_status}"
    fi
}

function polysquare_exit_with_failure_on_script_failures {
    exit "${__polysquare_script_failures}"
}

function polysquare_get_find_exclusions_arguments {
    local result=$1
    local cmd_append=""

    for exclusion in ${*:2} ; do
        if [ -d "${exclusion}" ] ; then
            cmd_append="${cmd_append} -not -path \"${exclusion}\"/*"
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
    local extensions_to_search=(${*:2})
    local last_element_index=$((${#extensions_to_search[@]} - 1))
    local cmd_append=""

    for index in "${!extensions_to_search[@]}" ; do
        cmd_append="${cmd_append} -name \"*.${extensions_to_search[$index]}\""
        if [ "$last_element_index" -gt "$index" ] ; then
            cmd_append="${cmd_append} -o"
        fi
    done

    eval "${result}='${cmd_append}'"
}

function polysquare_repeat_switch_for_list {
    local result=$1
    local switch=$2
    local list_items_to_repeat_switch_for=${*:3}
    local last_element_index=$((${#list_items_to_repeat_switch_for[@]} - 1))
    local list_with_repeated_switch=""

    for index in "${!list_items_to_repeat_switch_for[@]}" ; do
        local item="${list_items_to_repeat_switch_for[$index]}"
        list_with_repeated_switch+="${switch} ${item}"
        if [ "$last_element_index" -gt "$index" ] ; then
            list_with_repeated_switch="${list_with_repeated_switch} "
        fi
    done

    eval "${result}='${list_with_repeated_switch}'"
}

function polysquare_fetch_and_get_local_file {
    result=$1
    local url="${POLYSQUARE_HOST}/$2"
    local domain="$(echo "${url}" | cut -d/ -f1)"
    local path="${url#$domain}"
    local output_file="${POLYSQUARE_CI_SCRIPTS_DIR}/${path:1}"

    # Only download if we don't have the script already. This means
    # that if a project wants a newer script, it has to clear its caches.
    if ! [ -f "${output_file}" ] ; then
        curl -LSs "${url}" --create-dirs -o "${output_file}"
    fi

    eval "${result}='${output_file}'"
}

function polysquare_fetch {
    polysquare_fetch_and_get_local_file output_file "$@"
}

function polysquare_fetch_and_source {
    local fetched_file=""
    polysquare_fetch_and_get_local_file fetched_file "$1"
    source "${fetched_file}" "${@:2}"
}

function polysquare_fetch_and_eval {
    local fetched_file=""
    polysquare_fetch_and_get_local_file fetched_file "$1"
    eval "$(bash ${fetched_file} "${@:2}")"
}

function polysquare_fetch_and_fwd {
    local fetched_file=""
    polysquare_fetch_and_get_local_file fetched_file "$1"
    fetched_file_output="$(bash ${fetched_file} "${@:2}")"
    echo "${fetched_file_output}"
    eval "${fetched_file_output}"
}

function polysquare_fetch_and_exec {
    local fetched_file=""
    polysquare_fetch_and_get_local_file fetched_file "$1"
    bash "${fetched_file}" "${@:2}"
}

trap __polysquare_delete_script_outputs EXIT
