#!/usr/bin/env bash
# /travis/haskell-util.sh
#
# Travis CI Script which contains various utilities for
# for haskell activites, such as package installation
# (and binary downloads, if available)
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

# Special version of cabal_install for binaries that looks on
# public-travis-hs-binaries.polysquare.org for this system identifier 
# and downloads the relevant program into our previously-activated cabal
# binary PATH. This saves the time and effort of building the binary from
# scratch and maintaining a haskell installation.
function polysquare_cabal_install_binary {
    local binary="$1"

    polysquare_get_system_identifier sys_id
    local url="public-travis-hs-binaries.polysquare.org/${sys_id}/${binary}"
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
        polysquare_task "Installing ${binary} with cabal" \
            polysquare_fatal_error_on_failure \
                cabal install "${binary}"
    fi
}

