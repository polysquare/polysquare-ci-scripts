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
source "${POLYSQUARE_CI_SCRIPTS_DIR}/haskell-util.sh"

while getopts "d:v:f" opt "$@"; do
    case "$opt" in
    d) container_dir="$OPTARG"
       ;;
    v) haskell_version="$OPTARG"
       ;;
    f) force_haskell_installation="1"
       ;;
    esac
done

haskell_container_dir="${container_dir}/_languages/haskell"
haskell_build_dir="${haskell_container_dir}/haskell-build/"

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

    function polysquare_bootstrap_activate_haskell {
        local hs_ver_cont="${haskell_container_dir}/.hsenv_${haskell_version}"

        polysquare_eval_and_fwd \
            "export POLYSQUARE_HASKELL_ACTIVE_VERSION=${haskell_version};"
        polysquare_eval_and_fwd \
            "export POLYSQUARE_HASKELL_ACTIVE_CONTAINER=${hs_ver_cont};"

        # Export PATH for cabal/bin so that we can directly install binaries.
        polysquare_eval_and_fwd "export PATH=${hs_ver_cont}/cabal/bin:\${PATH}"
    }

    if ! [ -d "${haskell_build_dir}" ] ; then
        polysquare_task "Installing hsenv" polysquare_setup_hsenv
    fi

    if ! [ -z "${haskell_version}" ] ; then
        polysquare_task "Bootstrapping haskell version ${haskell_version}" \
            polysquare_bootstrap_activate_haskell
    fi

    if ! [ -z "${force_haskell_installation}" ] ; then
        polysquare_install_and_activate_haskell
    fi
}

polysquare_task "Setting up haskell" polysquare_setup_haskell
polysquare_exit_with_failure_on_script_failures
