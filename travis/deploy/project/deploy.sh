#!/bin/bash
# /travis/deploy/project/deploy.sh
#
# Copies locally installed packages into cache container, where they will be
# restored from later. Also deletes useless build artefacts which only
# take up space.
#
# As a result, to install more packages, the caches need to be flushed
# completely first.
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

languages=()

while getopts "d:l:" opt; do
    case "$opt" in
    d) container_dir=$OPTARG
       ;;
    l) languages+=("$OPTARG")
       ;;
    esac
done

function polysquare_run_if_dir_exists {
    if [ -d "$1" ] ; then
        eval "${*:2}"
    fi
}

function polysquare_prepare_caches {
    lang_rt_path="${container_dir}/_languages"

    function polysquare_copy_installation_dirs_to_cache_container {
        # shellcheck disable=SC2034
        local python_dirs=""
        # shellcheck disable=SC2034
        local ruby_dirs="gem"
        # shellcheck disable=SC2034
        local haskell_dirs="ghc cabal"
        # shellcheck disable=SC2034
        local node_dirs=""

        for lang in ${languages[*]} ; do
            dirs_variable="${lang}_dirs"
            for dir in ${!dirs_variable} ; do
                cp -TRf "${HOME}/.${dir}" "${lang_rt_path}/.${dir}"
            done
        done
    }

    function polysquare_cleanup_build_artefacts {
        function polysquare_cleanup_haskell_artefacts {
            local cabal_lib="${lang_rt_path}/.cabal/lib"
            find "${cabal_lib}" -type f -name "*.a" -execdir \
                rm -f ";" 2>/dev/null
            find "${cabal_lib}" -type f -name "*.o" -execdir \
                rm -f ";" 2>/dev/null
            find "${lang_rt_path}/.cabal/packages" -type f \
                -name "*.tar.gz" -execdir rm -f ";" 2>/dev/null
        }

        function polysquare_cleanup_python_artefacts {
            local python_dir="${lang_rt_path}/python"

            find "${python_dir}" -type f -name "*.pyc" -execdir \
                rm -f ";" 2>/dev/null
            find "${lang_rt_path}" -type d -name "__pycache__" -execdir \
                rm -rf ";" 2>/dev/null
        }

        function polysquare_cleanup_node_artefacts {
            cmd="find ${lang_rt_path}/node -type f -name \"package.json\""
            package_json_files=$(eval "${cmd}")
            for file in ${package_json_files} ; do
                touch -mt 0001010000 "${file}"
            done
        }

        polysquare_run_if_dir_exists "${lang_rt_path}/.cabal" \
            polysquare_task "Cleaning up haskell artefacts" \
                polysquare_cleanup_haskell_artefacts
        polysquare_run_if_dir_exists "${lang_rt_path}/python" \
            polysquare_task "Cleaning up python artefacts" \
                polysquare_cleanup_python_artefacts
        polysquare_run_if_dir_exists "${lang_rt_path}/node" \
            polysquare_task "Cleaning up node artefacts" \
                polysquare_cleanup_node_artefacts
    }

    polysquare_task "Copying language installations to container" \
        polysquare_fatal_error_on_failure \
            polysquare_copy_installation_dirs_to_cache_container

    polysquare_task "Cleaning up temporary build files" \
        polysquare_fatal_error_on_failure \
            polysquare_cleanup_build_artefacts
}

polysquare_task "Preparing container for caching" \
    polysquare_prepare_caches
polysquare_exit_with_failure_on_script_failures

