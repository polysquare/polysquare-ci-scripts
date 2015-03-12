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
        polysquare_fatal_error_on_failure which hsenv

        pushd "${haskell_container_dir}" > /dev/null 2>&1
        polysquare_fatal_error_on_failure \
            hsenv --ghc="${haskell_version}" --name="${haskell_version}"
        popd > /dev/null 2>&1
    }

    function polysquare_activate_haskell {
        local hs_ver_cont="${haskell_container_dir}/.hsenv_${haskell_version}"

        echo "if ! [ -z \"\${HSENV}\" ]; then deactivate_hsenv > /dev/null; fi;"
        echo "eval \"\$(cat ${hs_ver_cont}/bin/activate)\" > /dev/null;"
        echo "export POLYSQUARE_HASKELL_ACTIVE_VERSION=${haskell_version};"
        echo "export POLYSQUARE_HASKELL_ACTIVE_CONTAINER=${hs_ver_cont};"
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
