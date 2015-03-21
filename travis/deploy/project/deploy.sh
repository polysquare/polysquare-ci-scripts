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
            local haskell_dir="${lang_rt_path}/haskell"
        
            # Object code and dynamic libraries
            find "${haskell_dir}" -type f -name "*.o" -execdir rm -rf {} \; \
                2>/dev/null
            find "${haskell_dir}" -type f -name \
                "*_debug-ghc${haskell_version}.so" -execdir \
                    rm -rf {} \; 2>/dev/null
            find "${haskell_dir}" -type f -name "*_l-ghc${haskell_version}.so" \
                -execdir rm -rf {} \; 2>/dev/null

            # Profiling, debug, other libraries
            find "${haskell_dir}" -type f -name "lib*_p.a" -execdir \
                rm -rf {} \; 2>/dev/null
            find "${haskell_dir}" -type f -name "lib*_l.a" -execdir \
                rm -rf {} \; 2>/dev/null
            find "${haskell_dir}" -type f -name "lib*_thr.a" -execdir \
                rm -rf {} \; 2>/dev/null
            find "${haskell_dir}" -type f -name "lib*_debug.a" -execdir \
                rm -rf {} \; 2>/dev/null
            find "${haskell_dir}" -type f -name "*.p_*" -execdir rm -rf {} \; \
                2>/dev/null 
        }

        function polysquare_cleanup_python_artefacts {
            local python_dir="${lang_rt_path}/python"

            local cmd="find ${lang_rt_path}/python -type f -name \"*.pth\""
            local easy_install_pth_files=$(eval "${cmd}")

            find "${python_dir}" -type f -name "*.pyc" -execdir \
                rm -f ";" 2>/dev/null
            find "${lang_rt_path}" -type d -name "__pycache__" -execdir \
                rm -rf ";" 2>/dev/null
            for file in ${easy_install_pth_files} ; do
                touch -mt 0001010000 "${file}" 2>/dev/null
            done
        }

        function polysquare_cleanup_node_artefacts {
            cmd="find ${lang_rt_path}/node -type f -name \"package.json\""
            package_json_files=$(eval "${cmd}")
            for file in ${package_json_files} ; do
                touch -mt 0001010000 "${file}"
            done
        }

        polysquare_task "Cleaning up haskell artefacts" \
            polysquare_run_if_dir_exists "${lang_rt_path}/haskell" \
                polysquare_cleanup_haskell_artefacts
        polysquare_task "Cleaning up python artefacts" \
            polysquare_run_if_dir_exists "${lang_rt_path}/python" \
                polysquare_cleanup_python_artefacts
        polysquare_task "Cleaning up node artefacts" \
            polysquare_run_if_dir_exists "${lang_rt_path}/node" \
                polysquare_cleanup_node_artefacts
    }

    polysquare_task "Copying language installations to container" \
        polysquare_fatal_error_on_failure \
            polysquare_copy_installation_dirs_to_cache_container
    polysquare_task "Cleaning up temporary build files" \
        polysquare_cleanup_build_artefacts
    polysquare_task "Cleaning up cached CI scripts" \
        polysquare_fatal_error_on_failure rm -rf "${CONTAINER_DIR}/_scripts"
    polysquare_task "Cleaning up per-test caches" \
        polysquare_fatal_error_on_failure rm -rf "${CONTAINER_DIR}/_cache"
}

polysquare_task "Preparing container for caching" \
    polysquare_prepare_caches
polysquare_exit_with_failure_on_script_failures

