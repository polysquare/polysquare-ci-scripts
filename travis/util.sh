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
export POLYSQUARE_DOT_SLEEP="${POLYSQUARE_DOT_SLEEP-15}"
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

__polysquare_indent_level="${polysquare_indent_level-0}"
__polysquare_next_indent=0
function polysquare_apply_indent {
    # This function is designed to be piped to. It will read lines from the
    # standard input and indent them as appropriate (each indent is
    # four spaces, in line with task symbols)
    local whitespace=$(eval "printf \"%0.s \" {1..4}")
    while IFS='' read -n1 chr ; do
        # Special case, if this is the first character to be printed
        # then print the four spaces before it, so long as it isn't \n
        if [[ "${__polysquare_next_indent}" == "1" ]] && \
           [[ "${chr}" != "" ]] ; then
           >&2 printf "${whitespace}"
        fi

        >&2 printf "${chr}"

        if [[ "${chr}" == "" ]] ; then
            >&2 printf "\n${whitespace}"
        fi

        __polysquare_next_indent=0
    done
}

# This variable is used by polysquare_monitor_command_* in order to print
# a \n when the very first line of output is hit.
__polysquare_initial_carriage_return=0
function polysquare_task {
    local description="$1"
    local function_name="$2"

    local last_indent_level="${__polysquare_indent_level}"
    (( __polysquare_indent_level++ ))
    __polysquare_next_indent=1
    __polysquare_initial_carriage_return=1
    # If the indent level is zero, use =>, otherwise use
    # [whitespace for (indent level * 3)]...
    if [ "${last_indent_level}" -eq "0" ] ; then
        >&2 printf "\n=> ${description}"
    else
        >&2 printf "\n... ${description}"
    fi

    # Use command substituion to only filter stderr
    eval "${function_name}" 2> >(polysquare_apply_indent)
    (( __polysquare_indent_level-- ))
}

__polysquare_script_output_files=()
function __polysquare_delete_script_outputs {
    for output_file in "${__polysquare_script_output_files[@]}" ; do
        rm -rf "${output_file}"
    done
}

function _polysquare_monitor_command_internal_prologue {
    local printer_pid_return="$1"


    if [ -z "${_POLYSQUARE_DONT_PRINT_DOTS}" ] ; then
        echo "printing dots ${POLYSQUARE_DOT_SLEEP}"
        echo "while :; sleep ${POLYSQUARE_DOT_SLEEP}; do printf '.'; done" \
            | bash 2> /dev/null 1>&2 &
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

    if [[ "${__polysquare_initial_carriage_return}" == "1" ]] ; then
        >&2 printf "\n"
        __polysquare_initial_carriage_return=0
    fi

    >&2 eval "${concat_cmd}"
    local result=$?

    eval "${script_status_return}='${result}'"
}

function __polysquare_convert_message_to_status {
    local status_return=$1
    local message=$2

    local messages=("Done", \
                    "Hung up", \
                    "Illegal Instruction" \
                    "Aborted" \
                    "Killed" \
                    "Segmentation Fault" \
                    "Terminated" \
                    "Stopped")
    local statuses=(0 \
                    1 \
                    4 \
                    6 \
                    11 \
                    15 \
                    17)

    local _internal_status=1

    for i in "${!messages[@]}"; do
        if [ "${messages[$i]}" = "${message}" ] ; then
            _internal_status="${statuses[$i]}"
        fi
    done

    eval "${status_return}"="'${_internal_status}'"
}

function polysquare_monitor_command_output {
    local script_status_return="$1"
    local script_output_return="$2"
    local cmd=$(echo "${*:3}" | xargs echo)
    local output="$(mktemp -t psq-util-sh.XXXXXX)"
    local result=0
    __polysquare_script_output_files+=("${output}")

    local start_time=$(date +"%s")

    # Execute the process - create a named pipe where we will watch for
    # its exit code, but redirect all output to ${output}
    local fifo=$(mktemp /tmp/psq-monitor-fifo.XXXXXX)
    rm -f "${fifo}"
    mkfifo "${fifo}"
    exec 3<>"${fifo}" # Open fifo pipe for read/write.
    (eval "${cmd} > ${output} 2>&1"; echo "$?" > "${fifo}") &

    # This is effectively a tool to feed the travis-ci script
    # watchdog. Print a dot every POLYSQUARE_DOT_SLEEP seconds (waiting
    # one second between checking each time to avoid spinning too much)
    while true ; do
        # Check every second whether or not there was some input on the
        # file descriptor
        read -t 1 -u 3 result
        if [[ "$?" != "0" ]] ; then
            if [[ -z "${_POLYSQUARE_DONT_PRINT_DOTS}" ]] ; then
                local current_time=$(date +"%s")
                local time_delta=$((current_time - start_time))

                if [ "${time_delta}" -ge "${POLYSQUARE_DOT_SLEEP}" ] ; then
                    start_time="${current_time}"
                    >&2 printf "."
                fi
            fi
        else
            break
        fi
    done

    3<&- # Close file descriptor
    rm -f "${fifo}"

    eval "${script_status_return}='${result}'"
    eval "${script_output_return}='${output}'"
}

__polysquare_script_failures=0;
function polysquare_note_failure_and_continue {
    local status_return="$1"
    local concat_cmd=$(echo "${*:2}" | xargs echo)
    polysquare_monitor_command_status status "${concat_cmd}"
    if [[ "${status}" != "0" ]] ; then
        (( __polysquare_script_failures++ ))
    fi

    eval "${status_return}='${status}'"
}

function polysquare_report_failures_and_continue {
    local status_return="$1"
    local concat_cmd=$(echo "${*:2}" | xargs echo)
    polysquare_monitor_command_output status output_file "${concat_cmd}"

    if [[ "${status}" != "0" ]] ; then
        __polysquare_initial_carriage_return=0
        printf "\n"
        >&2 cat "${output_file}"
        (( __polysquare_script_failures++ ))
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

    if [[ "${exit_status}" != "0" ]] ; then
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
