#!/usr/bin/env bash
# /travis/haskell-util.sh
#
# Travis CI Script which contains various utilities for
# for haskell activites, such as package installation
# (and binary downloads, if available)
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

cabal_config_append=$(cat << EOF
library-profiling: False
executable-dynamic: False
split-objs: True
documentation: False
tests: False
EOF
)

# This function lazy-installs and bootstraps haskell, based on the version
# selected earlier with polysquare_setup_haskell. We avoid installing haskell
# if we can - it is very large and inflates cache sizes substantially. This
# should be run inside a function which is having its output captured and
# evaluated, eg, inside of a setup script.
function polysquare_install_and_activate_haskell {
    haskell_container_dir="${CONTAINER_DIR}/_languages/haskell"
    haskell_build_dir="${haskell_container_dir}/haskell-build/"
    haskell_version="${POLYSQUARE_HASKELL_ACTIVE_VERSION?}"

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
        local hs_ver_cont="${POLYSQUARE_HASKELL_ACTIVE_CONTAINER?}"

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
        local hs_ver_cont="${POLYSQUARE_HASKELL_ACTIVE_CONTAINER?}"
        local hslib="${haskell_build_dir}/usr/lib"

        # Deactivate the hsenv properly first if that's possible, otherwise
        # just unset the HSENV variable and clobber what we have (as it was
        # probably just inherited from a parent shell)
        polysquare_eval_and_fwd "declare -f deactivate_hsenv > /dev/null && "\
                                "deactivate_hsenv > /dev/null;"
        polysquare_eval_and_fwd "unset -v HSENV;"
        polysquare_eval_and_fwd "eval \"\$(cat ${hs_ver_cont}/bin/activate)\"" \
                                "> /dev/null;"
        polysquare_eval_and_fwd "export LIBRARY_PATH=${hslib}:\${LIBRARY_PATH};"
    }

    if ! [ -d "${POLYSQUARE_HASKELL_ACTIVE_CONTAINER?}" ] ; then
        polysquare_task "Installing haskell version ${haskell_version}" \
            polysquare_install_haskell
    fi
    
    polysquare_task "Activating haskell version ${haskell_version}" \
        polysquare_activate_haskell
}

# Special version of cabal_install for binaries that looks on
# public-travis-hs-binaries.polysquare.org for this system identifier 
# and downloads the relevant program into our previously-activated cabal
# binary PATH. This saves the time and effort of building the binary from
# scratch and maintaining a haskell installation.
function polysquare_cabal_install_binary {
    local binary="$1"

    polysquare_get_system_identifier sys_id
    local url="public-travis-hs-binaries.polysquare.org/${sys_id?}/${binary}"
    local hs_ver_cont="${POLYSQUARE_HASKELL_ACTIVE_CONTAINER}"
    local output_file="${hs_ver_cont}/cabal/bin/${binary}"

    function polysquare_download_binary_version {
        polysquare_download_file_if_output_unavailable \
            "${output_file}" "${url}"
        chmod +x "${output_file}"
    }

    if curl -LSs --head --fail "${url}" > /dev/null 2>&1; then
        polysquare_task "Downloading binary version of ${binary}" \
            polysquare_download_binary_version
    else
        polysquare_install_and_activate_haskell
        polysquare_task "Installing ${binary} with cabal" \
            polysquare_fatal_error_on_failure \
                cabal install "${binary}"
    fi
}

