#!/usr/bin/env bash
# /travis/deploy/shell/deploy.sh
#
# Travis CI Script which forwards on to the project deployment script.
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

while getopts "d:" opt; do
    case "$opt" in
    d) container_dir=$OPTARG
       ;;
    esac
done


polysquare_note_failure_and_continue status \
    polysquare_fetch_and_exec deploy/project/deploy.sh \
        -d "${container_dir}" -l "haskell" -l "ruby" -l "python" -l "node"
polysquare_exit_with_failure_on_script_failures
