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

    function polysquare_cleanup_build_artefacts {
        function polysquare_cleanup_haskell_artefacts {
            local haskell_dir="${lang_rt_path}/haskell"
        
            # Object code and dynamic libraries
            find "${haskell_dir}" -type f -name "*.o" -delete 2>/dev/null
            find "${haskell_dir}" -type f -name \
                "*_debug-ghc*.so" -delete 2>/dev/null
            find "${haskell_dir}" -type f -name "*_l-ghc*.so" \
                -delete  2>/dev/null

            # Profiling, debug, other libraries
            find "${haskell_dir}" -type f -name "lib*_p.a" -delete 2>/dev/null
            find "${haskell_dir}" -type f -name "lib*_l.a" -delete 2>/dev/null
            find "${haskell_dir}" -type f -name "lib*_thr.a" -delete 2>/dev/null
            find "${haskell_dir}" -type f -name "lib*_debug.a" -delete \
                2>/dev/null
            find "${haskell_dir}" -type f -name "*.p_*" -delete 2>/dev/null
        }

        function polysquare_cleanup_python_artefacts {
            local python_dir="${lang_rt_path}/python"

            find "${python_dir}" -type f -name "easy-install.pth" -delete \
                2>/dev/null
            find "${python_dir}" -type f -name "*.pyc" -delete 2>/dev/null
            find "${python_dir}" -type f -name "*.egg-link" -delete 2>/dev/null
            find "${lang_rt_path}" -type d -name "__pycache__" -delete \
                2>/dev/null
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

    polysquare_task "Cleaning up temporary build files" \
        polysquare_cleanup_build_artefacts
    polysquare_task "Cleaning up cached CI scripts" \
        polysquare_fatal_error_on_failure rm -rf "${container_dir}/_scripts"

    # Our fifos and other operational data is in here, so we have to
    # use rm -rf directly instead of polysquare_fatal_error_on_failure
    polysquare_task "Cleaning up per-test caches" \
        rm -rf "${container_dir}/_cache" > /dev/null 2>&1
}

polysquare_task "Preparing container for caching" \
    polysquare_prepare_caches
polysquare_exit_with_failure_on_script_failures

