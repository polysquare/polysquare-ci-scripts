#!/usr/bin/env bash
# /travis/check/python/deploy.sh
#
# Travis CI Script which runs python and project specific tasks to prepare
# for deployment. It runs during the "script" phase whilst we still have
# access to all our environment variables.
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

while getopts "d:" opt; do
    case "$opt" in
    d) container_dir=$OPTARG
       ;;
    esac
done

function polysquare_make_python_doc_converters_available_at_deploy {
    # VIRTUAL_ENV/bin stays executable during a python build, so
    # put symlinks to pandoc in there
    while IFS= read -r -d '' path ; do
        file=$(basename "${path}")
        polysquare_fatal_error_on_failure ln -s \
            "${path}" "${VIRTUAL_ENV}/bin/${file}"
    done < <(find "${HOME}/virtualenv/.cabal/bin" -type f -print0)
}

polysquare_task "Preparing documentation converters for deploy step" \
    polysquare_make_python_doc_converters_available_at_deploy

polysquare_note_failure_and_continue status \
    polysquare_fetch_and_exec prepare-lang-cache.sh \
        -d "${container_dir}" -l "haskell" -l "ruby"
polysquare_exit_with_failure_on_script_failures
