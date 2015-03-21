#!/usr/bin/env bash
# /travis/setup/project/haskell_setup.sh
#
# Travis CI script to set up a self-contained instance of haskell-build
# and separate haskell installations. The output of this script should be
# evaluated directly, for instance
#
#     eval $(curl -LSs http://path/to/setup/project/setup_haskell.sh | bash)
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

while getopts "d:v:" opt "$@"; do
    case "$opt" in
    d) container_dir="$OPTARG"
       ;;
    v) haskell_version="$OPTARG"
       ;;
    esac
done

haskell_container_dir="${container_dir}/_languages/haskell"
haskell_build_dir="${haskell_container_dir}/haskell-build/"

cabal_config_append=$(cat << EOF
library-profiling: False
executable-dynamic: False
split-objs: True
documentation: False
tests: False
EOF
)

function polysquare_setup_haskell {
    mkdir -p "${haskell_container_dir}"

    function polysquare_setup_hsenv {
        # Set up a hsenv.sh installation.
        mkdir -p "${haskell_build_dir}"
        pushd "${haskell_container_dir}" > /dev/null 2>&1
        polysquare_task "Downloading hsenv" \
            polysquare_fatal_error_on_failure \
                git clone git://github.com/saturday06/hsenv.sh \
                    "${haskell_build_dir}"
        polysquare_fatal_error_on_failure mkdir -p \
            "${haskell_build_dir}/usr/lib/ghc"
        polysquare_fatal_error_on_failure ln -s \
            /usr/lib/x86_64-linux-gnu/libgmp.so.10 \
            "${haskell_build_dir}/usr/lib/ghc/libgmp.so"
        polysquare_fatal_error_on_failure ln -s \
            /usr/lib/x86_64-linux-gnu/libgmp.so.10 \
            "${haskell_build_dir}/usr/lib/libgmp.so"
        polysquare_fatal_error_on_failure ln -s \
            /usr/lib/x86_64-linux-gnu/libffi.so.6 \
            "${haskell_build_dir}/usr/lib/ghc/libffi.so"
        polysquare_fatal_error_on_failure ln -s \
            /usr/lib/x86_64-linux-gnu/libffi.so.6 \
            "${haskell_build_dir}/usr/lib/libffi.so"
        popd > /dev/null 2>&1
    }

    function polysquare_install_haskell {
        # Install a haskell version. This will require us to:
        # 1. Put hsenv in our PATH
        # 2. Change to the directory where we'll be putting our
        #    haskell environments
        #
        # This command will fail if the nominated haskell version cannot be
        # installed on the target platform (either because it doesn't exist or
        # or for some other reason).
        export PATH="${haskell_build_dir}/bin:${PATH}"
        export LIBRARY_PATH="${haskell_build_dir}/usr/lib:${LIBRARY_PATH}"
        polysquare_fatal_error_on_failure which hsenv

        pushd "${haskell_container_dir}" > /dev/null 2>&1
        polysquare_fatal_error_on_failure \
            hsenv --ghc="${haskell_version}" --name="${haskell_version}"
        popd > /dev/null 2>&1
        
        # Get rid of stuff we don't need
        local hs_ver_cont="${haskell_container_dir}/.hsenv_${haskell_version}"

        # Haskell compiler and cabal bootstrap source code
        polysquare_fatal_error_on_failure rm -rf "${hs_ver_cont}/src"
        polysquare_fatal_error_on_failure rm -rf "${hs_ver_cont}/tmp"
        polysquare_fatal_error_on_failure rm -rf "${hs_ver_cont}/cache"
        polysquare_fatal_error_on_failure rm -rf \
            "${hs_ver_cont}/cabal/bootstrap/lib"

        # Object code and dynamic libraries
        find "${hs_ver_cont}" -type f -name "*.o" -execdir rm -rf {} \; \
            2>/dev/null
        find "${hs_ver_cont}" -type f -name "*_debug-ghc${haskell_version}.so" \
            -execdir rm -rf {} \; 2>/dev/null
        find "${hs_ver_cont}" -type f -name "*_l-ghc${haskell_version}.so" \
            -execdir rm -rf {} \; 2>/dev/null

        # Profiling, debug, other libraries
        find "${hs_ver_cont}" -type f -name "lib*_p.a" -execdir rm -rf {} \; \
            2>/dev/null
        find "${hs_ver_cont}" -type f -name "lib*_l.a" -execdir rm -rf {} \; \
            2>/dev/null
        find "${hs_ver_cont}" -type f -name "lib*_thr.a" -execdir rm -rf {} \; \
            2>/dev/null
        find "${hs_ver_cont}" -type f -name "lib*_debug.a" -execdir \
            rm -rf {} \; 2>/dev/null
        find "${hs_ver_cont}" -type f -name "*.p_*" -execdir rm -rf {} \; \
            2>/dev/null 

        # Documentation (~100Mb)
        polysquare_fatal_error_on_failure rm -rf "${hs_ver_cont}/ghc/share/doc"
        
        # Logs and other temporary files
        polysquare_fatal_error_on_failure rm -rf \
            "${haskell_build_dir}/tmp"
        polysquare_fatal_error_on_failure rm -rf "${hs_ver_cont}/hsenv.log"
        
        # Disable library-profiling and documentation building
        echo "${cabal_config_append}" >> "${hs_ver_cont}/cabal/config"
    }

    function polysquare_activate_haskell {
        local hs_ver_cont="${haskell_container_dir}/.hsenv_${haskell_version}"
        local hs_lib_path="${haskell_build_dir}/usr/lib"

        # Deactivate the hsenv properly first if that's possible, otherwise
        # just unset the HSENV variable and clobber what we have (as it was
        # probably just inherited from a parent shell)
        echo "declare -f deactivate_hsenv > /dev/null && "\
             "deactivate_hsenv > /dev/null;"
        echo "unset -v HSENV;"
        echo "eval \"\$(cat ${hs_ver_cont}/bin/activate)\" > /dev/null;"
        echo "export POLYSQUARE_HASKELL_ACTIVE_VERSION=${haskell_version};"
        echo "export POLYSQUARE_HASKELL_ACTIVE_CONTAINER=${hs_ver_cont};"
        echo "export LIBRARY_PATH=${hs_lib_path}:\${LIBRARY_PATH};"
    }

    if ! [ -d "${haskell_build_dir}" ] ; then
        polysquare_task "Installing hsenv" polysquare_setup_hsenv
    fi

    if ! [ -d "${haskell_container_dir}/${haskell_version}" ] ; then
        polysquare_task "Installing haskell version ${haskell_version}" \
            polysquare_install_haskell
    fi

    if ! [ -z "${haskell_version}" ] ; then
        polysquare_task "Activating haskell version ${haskell_version}" \
            polysquare_activate_haskell
    fi
}

polysquare_task "Setting up haskell" polysquare_setup_haskell
polysquare_exit_with_failure_on_script_failures
