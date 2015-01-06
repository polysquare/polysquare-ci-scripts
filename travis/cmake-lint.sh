#!/usr/bin/env bash
# /travis/cmake-lint.sh
#
# Travis CI Script to lint CMake files for common errors.
#
# See LICENCE.md for Copyright information

printf "\n=> Linting CMake files"
while getopts "x:n:" opt; do
    case "$opt" in
    x) exclusions+=" $OPTARG"
       ;;
    n) namespace="$OPTARG"
       ;;
    esac
done

failures=0

function check_status_of() {
    output_file=$(mktemp /tmp/tmp.XXXXXXX)
    concat_cmd=$(echo "$@" | xargs echo)
    eval "${concat_cmd}" > "${output_file}" 2>&1  &
    command_pid=$!
    
    # This is effectively a tool to feed the travis-ci script
    # watchdog. Print a dot every sixty seconds.
    echo "while :; sleep 60; do printf '.'; done" | bash 2> /dev/null &
    printer_pid=$!
    
    wait "${command_pid}"
    command_result=$?
    kill "${printer_pid}"
    wait "${printer_pid}" 2> /dev/null
    if [[ $command_result != 0 ]] ; then
        failures=$((failures + 1))
        printf "\n"
        cat "${output_file}"
        printf "\nA subcommand failed. "
        printf "Consider deleting the travis build cache.\n"
    fi
}

function get_exclusions_arguments() {
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

printf "\n   ... Installing linters "
check_status_of pip install cmakelint polysquare-cmake-linter

printf "\n   ... Running linters"
get_exclusions_arguments excl
lint_cmake_modules_cmd="find . -type f -name \"*.cmake\" ${excl} -print0 | xargs -L1 -0 echo"
lint_cmake_lists_cmd="find . -type f -name \"CMakeLists.txt\" ${excl} -print0 | xargs -L1 -0 echo"
lint_cmake_modules=$(eval "${lint_cmake_modules_cmd}")
lint_cmake_lists=$(eval "${lint_cmake_lists_cmd}")

# We filter whitespace/extra and whitespace/indent out
# as those checks don't enforce our own style guide.
cmakelint_cmd="cmakelint
--spaces=4
--filter=-whitespace/extra,-whitespace/indent,-linelength
"

polysquare_cmake_linter_cmd="polysquare-cmake-linter
--blacklist
access/other_private
--namespace ${namespace}
--indent 4
"

for lint_file in ${lint_cmake_modules} ${lint_cmake_lists} ; do
    # CMakeLint does not return an exit code, so capture its output
    # and check if it is more than just whitespace. It always puts some
    # whitespace in the output upon passing.
    cmd=$(echo "${cmakelint_cmd} ${lint_file}" | xargs echo)
    output=$(eval "${cmd}" 2>/dev/null)
    if ! [[ -z "${output}" ]] ; then
        failures=$((failures + 1))
        echo "${output}"
    fi

    check_status_of "${polysquare_cmake_linter_cmd} ${lint_file}"
done

printf "\n"
exit "${failures}"
