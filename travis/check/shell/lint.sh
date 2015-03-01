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

# These two functions were adapted from the Bash
# Automated Testing System.
#
# Copyright (c) 2014 Sam Stephenson, licenced under
# the MIT license.
function _polysquare_resolve_link {
  $(type -p greadlink readlink | head -1) "$1"
}

function _polysquare_abs_dirname {
  local cwd="$(pwd)"
  local path="$1"

  while [ -n "$path" ]; do
    cd "${path%/*}"
    local name="${path##*/}"
    path="$(_polysquare_resolve_link "$name" || true)"
  done

  pwd
  cd "$cwd"
}

function polysquare_check_shell_files {
    local excl
    local ext
    local shell_files
    local bats_files

    # Find all the normal shell files first
    polysquare_get_find_exclusions_arguments excl "${exclusions}"
    polysquare_get_find_extensions_arguments ext "sh bash"

    for directory in ${directories} ; do
        cmd="polysquare_sorted_find ${directory} -type f ${ext} ${excl}"
        shell_files+=$(eval "${cmd}")
        shell_files+=" "
    done

    # For BATS files, we need to pre-process them first. Read
    # the link target of bats and then find the bats-preprocess
    # executable. Use that on all found bats files and pre-process
    # them into temporary files with a similar FS structure. Add
    # those to the files to lint.
    for dir in ${directories} ; do
        cmd="polysquare_sorted_find ${dir} -type f -name \"*.bats\" ${excl}"
        bats_files+=$(eval "${cmd}")
        bats_files+=" "
    done

    # Will be deleted at the end of this script
    local temp_bats_files_dir=$(mktemp -d /tmp/psq-extracted-bats.XXXXXX)
    local abs_path_to_bats=$(_polysquare_abs_dirname "$(which bats)")
    local bats_preprocess_executable="${abs_path_to_bats}/bats-preprocess"
    for file in ${bats_files} ; do
        local containing_dir="${temp_bats_files_dir}/${file%/*}"
        local output_file="${temp_bats_files_dir}/${file##*/}"
        mkdir -p "${containing_dir}"
        eval "${bats_preprocess_executable} < ${file} > ${output_file}"
        sed -i "s/env bats/env bash/g" "${output_file}"

        shell_files+="${output_file} "
    done

    polysquare_task "Linting shell files with shellcheck" \
        polysquare_check_files_with shellcheck "${shell_files}"
    polysquare_task "Linting shell files with bashlint" \
        polysquare_check_files_with bashlint "${shell_files}"

    rm -rf "${temp_bats_files_dir}"
}

polysquare_task "Linting shell files" polysquare_check_shell_files
polysquare_exit_with_failure_on_script_failures
