#!/usr/bin/env bash
# /travis/setup/project/language.sh
#
# Travis CI script to set up self-contained versions of
# scripting languages and their packaging systems. This script
# shouldn't be used directly, but instead in conjunction with another
# script that you execute the output of directly, for instance:
#
#     eval $(curl -LSs http://path/to/setup/project.sh | bash)
#
# The following switches affect the operation of this script:
# -l: Specifies a language to set up. Can be passed more than once.
# -d: Where the Travis CI cache is being stored. Default is
#     ${HOME}/container
# -s: Version of python to set up. Default is 2.7
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

function polysquare_setup_haskell {
    # Setup ghc binary distribution. We need to:
    # 1. Download the packages
    # 2. Replace symlink for /var/lib/ghc/package.conf.d
    # 3. Replace hardcoded paths in binary wrappers as
    #    well as those in the package database
    # 4. Add usr/bin and usr/lib to PATH
    # 5. Add ~/.cabal/bin to PATH
    # 5. Initialize ghc package cache
    # 6. Refresh cabal repositories
    # 7. Symlink libgmp and libffi to both usr/lib and
    #    usr/lib/ghc

    function polysquare_download_haskell_packages {
        mkdir -p "${HOME}/.polysquare-haskell-download-cache" > /dev/null 2>&1
        pushd "${HOME}/.polysquare-haskell-download-cache" > /dev/null 2>&1
        polysquare_fatal_error_on_failure apt-get download ghc cabal-install
        popd > /dev/null 2>&1
    }

    function polysquare_extract_haskell_packages {
        find "${HOME}/.polysquare-haskell-download-cache" -maxdepth 1 \
            -type f -name "*.deb" -print0 | \
                xargs -L 1 -0 -I {} dpkg-deb --extract {} \
                    "${LANG_RT_PATH}" 2>&1
    }

    function polysquare_adjust_haskell_package_paths {
        polysquare_fatal_error_on_failure rm \
            "${LANG_RT_PATH}/usr/lib/ghc/package.conf.d"
        polysquare_fatal_error_on_failure ln -s \
            "${LANG_RT_PATH}/var/lib/ghc/package.conf.d" \
            "${LANG_RT_PATH}/usr/lib/ghc/package.conf.d"

        for filename in ghc ghci ghc-pkg haddock-ghc-7.4.1 hsc2hs runghc ; do
            polysquare_fatal_error_on_failure sed -i \
                "s:/usr:${LANG_RT_PATH}/usr:" \
                "${LANG_RT_PATH}/usr/bin/${filename}"
            polysquare_fatal_error_on_failure sed -i \
                "s:/var:${LANG_RT_PATH}/var:" \
                "${LANG_RT_PATH}/usr/bin/${filename}"
        done

        find "${LANG_RT_PATH}/var/lib/ghc/package.conf.d" \
            -name "*.conf" -type f -print0 | \
                xargs -L 1 -0 sed -i "s:/usr:${LANG_RT_PATH}/usr:" 2>&1

        polysquare_fatal_error_on_failure ln -s \
            /usr/lib/x86_64-linux-gnu/libgmp.so.10 \
            "${LANG_RT_PATH}/usr/lib/ghc/libgmp.so"
        polysquare_fatal_error_on_failure ln -s \
            /usr/lib/x86_64-linux-gnu/libgmp.so.10 \
            "${LANG_RT_PATH}/usr/lib/libgmp.so"
        polysquare_fatal_error_on_failure ln -s \
            /usr/lib/x86_64-linux-gnu/libffi.so.6 \
            "${LANG_RT_PATH}/usr/lib/ghc/libffi.so"
        polysquare_fatal_error_on_failure ln -s \
            /usr/lib/x86_64-linux-gnu/libffi.so.6 \
            "${LANG_RT_PATH}/usr/lib/libffi.so"

        polysquare_fatal_error_on_failure mkdir -p "${LANG_RT_PATH}/cabal"
        polysquare_fatal_error_on_failure mkdir -p "${LANG_RT_PATH}/ghc"
    }

    function polysquare_update_ghc_package_cache {
        polysquare_fatal_error_on_failure ghc-pkg recache
    }

    function polysquare_update_cabal_repositories {
        if ! [ -f "${HOME}/.polysquare-cabal-updated" ] ; then
            polysquare_fatal_error_on_failure cabal update
        fi

        touch "${HOME}/.polysquare-cabal-updated" > /dev/null 2>&1
    }

    function polysquare_create_haskell_home_dirs {
        polysquare_fatal_error_on_failure mkdir -p "${HOME}/.ghc"
        polysquare_fatal_error_on_failure mkdir -p "${HOME}/.cabal"
    }

    polysquare_task "Downloading packages" polysquare_download_haskell_packages
    polysquare_task "Extracting packages" polysquare_extract_haskell_packages
    polysquare_task "Adjusting package paths" \
        polysquare_adjust_haskell_package_paths

    # For the purposes of ghc-pkg we need to set PATH and LD_LIBRARY_PATH here
    export PATH=${LANG_RT_PATH}/usr/bin:${PATH}
    export LD_LIBRARY_PATH=${LANG_RT_PATH}/usr/lib:${LD_LIBRARY_PATH}

    polysquare_task "Updating GHC package cache" \
        polysquare_update_ghc_package_cache
    polysquare_task "Updating cabal repositories" \
        polysquare_update_cabal_repositories
    polysquare_task "Creating haskell home directories" \
        polysquare_create_haskell_home_dirs
}

function polysquare_setup_python {
    function polysquare_install_virtualenv {
        polysquare_fatal_error_on_failure easy_install \
            --prefix "${LANG_RT_PATH}/usr/" virtualenv
    }

    function polysquare_create_virtualenv {
        polysquare_fatal_error_on_failure \
            "${LANG_RT_PATH}/usr/bin/virtualenv" \
            "--python=/usr/bin/python${python_version}" \
            "${LANG_RT_PATH}/python"
    }

    python_prefix="lib/python${python_version}/site-packages"
    next_pythonpath="${LANG_RT_PATH}/usr/${python_prefix}"

    polysquare_fatal_error_on_failure mkdir -p "${next_pythonpath}"

    # We need to export PYTHONPATH for the purposes of this script
    # too, so that easy_install and virtualenv do not fail
    export PYTHONPATH=${next_pythonpath}:${PYTHONPATH}

    polysquare_task "Installing virtualenv" polysquare_install_virtualenv
    polysquare_task "Creating virtualenv for ${python_version}" \
        polysquare_create_virtualenv
}

function polysquare_setup_node {
    function polysquare_install_nodeenv {
        # Setup pythonpath for nodeenv, as we'll need it
        python_prefix="lib/python${python_version}/site-packages"
        next_pythonpath="${LANG_RT_PATH}/usr/${python_prefix}"
        export PYTHONPATH=${next_pythonpath}:${PYTHONPATH}

        polysquare_fatal_error_on_failure easy_install \
            --prefix "${LANG_RT_PATH}/usr/" nodeenv
    }

    function polysquare_create_nodeenv {
        polysquare_fatal_error_on_failure "${LANG_RT_PATH}/usr/bin/nodeenv" \
            --prebuilt "${LANG_RT_PATH}/node"
        rm -rf "${LANG_RT_PATH}/node/src/"
        rm -rf "${LANG_RT_PATH}/node/lib/node_modules/npm/doc/"
        rm -rf "${LANG_RT_PATH}/node/lib/node_modules/npm/man/"
        rm -rf "${LANG_RT_PATH}/node/lib/node_modules/npm/html/"
    }

    polysquare_task "Installing nodeenv" polysquare_install_nodeenv
    polysquare_task "Creating nodeenv" polysquare_create_nodeenv
}

function polysquare_setup_ruby {
    # Install rvm
    function polysquare_install_rvm {
        local rvm_script=$(mktemp /tmp/psq-rvm-install.XXXXXX)
        curl -LSs https://get.rvm.io > "${rvm_script}"

        polysquare_fatal_error_on_failure \
            bash "${rvm_script}" --ignore-dotfiles

        source "${HOME}/.rvm/scripts/rvm"
        rvm autolibs read-only

        # It seems like this is required for when we enter a new shell
        # during the cache upload phase.
        echo rvm_auto_reload_flag=1 >> ~/.rvmrc
    }

    # Set PATH to have ruby as the first entry to supprss a warning
    export PATH=${HOME}/.rvm/gems/${ruby_version}/bin:${PATH}

    polysquare_task "Installing rvm" polysquare_install_rvm

    # Use rvm to install ruby 1.9.3-p551
    polysquare_task "Installing ruby 1.9.3 using rvm" \
        polysquare_fatal_error_on_failure rvm install 1.9.3-p551

    # Just make the 'gems' directory, so that we can copy them later.
    polysquare_fatal_error_on_failure mkdir -p "${LANG_RT_PATH}/gems"
    polysquare_fatal_error_on_failure mkdir -p "${HOME}/.gem"
}

# Parse options and then call the setup functions for each script
python_version=2.7
ruby_version=ruby-1.9.3-p551

while getopts "d:l:s:r:" opt "$@"; do
    case "$opt" in
    d) container_dir="$OPTARG"
       ;;
    l) languages+=" $OPTARG"
       ;;
    s) python_version="$OPTARG"
       ;;
    r) ruby_version="$OPTARG"
       ;;
    esac
done

LANG_RT_PATH="${container_dir}/_languages"

function polysquare_install_language_runtimes {
    polysquare_fatal_error_on_failure mkdir -p "${LANG_RT_PATH}"
    pushd "${LANG_RT_PATH}" > /dev/null 2>&1

    for l in ${languages} ; do
        eval "polysquare_task \"Setting up ${l}\" polysquare_setup_${l}"
    done

    touch "${LANG_RT_PATH}/done-stamp"

    popd > /dev/null 2>&1
}

function polysquare_restore_language_runtimes_from_cache {
    # These variables are not really unused - they're used, but only by
    # a compound statement, so shellcheck won't detect that.
    # shellcheck disable=SC2034
    local python_dirs=""
    # shellcheck disable=SC2034
    local ruby_dirs="gem"
    # shellcheck disable=SC2034
    local haskell_dirs="ghc cabal"
    # shellcheck disable=SC2034
    local node_dirs=""

    for lang in ${languages} ; do
        dirs_variable="${lang}_dirs"
        for dir in ${!dirs_variable} ; do
            # Only do the move if these directories do not exist on the host
            if ! [ -d "${HOME}/.${dir}" ]  ; then
                polysquare_fatal_error_on_failure cp -TRf \
                    "${LANG_RT_PATH}/.${dir}" "${HOME}/.${dir}"
            fi
        done
    done
}

function polysquare_activate_languages {
    local rvm_rubies_path="${HOME}/.rvm/rubies"
    local rvm_rubies_lib="${rvm_rubies_path}/${ruby_version}/lib"
    local gem_user_dir=$(ruby -rubygems -e 'puts Gem.user_dir')

    echo "export PATH=${LANG_RT_PATH}/usr/bin:\${PATH};"
    echo "export PATH=${HOME}/.cabal/bin:\${PATH};"
    echo "export PATH=${gem_user_dir}/bin:$PATH:\${PATH};"
    echo "export PATH=${LANG_RT_PATH}/python/bin:\${PATH};"
    echo "export PATH=${LANG_RT_PATH}/node/bin:\${PATH};"
    echo "export PATH=${rvm_rubies_path}/${ruby_version}/bin:\${PATH};"

    # We don't include the old PYTHONPATH in the current PYTHONPATH so
    # that pip doesn't favor installed packages from other virtual
    # environments.
    echo "export PYTHONPATH=${next_pythonpath};"
    echo "export PYTHONDONTWRITEBYTECODE=1;"
    echo "export LD_LIBRARY_PATH=${rvm_rubies_lib}:\${LD_LIBRARY_PATH};"
    echo "export LD_LIBRARY_PATH=${LANG_RT_PATH}/usr/lib:\${LD_LIBRARY_PATH};"
    echo "export VIRTUAL_ENV=${LANG_RT_PATH}/python;"
    echo "export PYTHON_SETUP_LOCALLY=1;"
    echo "export GEM_PATH=${HOME}/.rvm/gems/${ruby_version}@global:${GEM_PATH};"
    echo "export GEM_PATH=${gem_user_dir}:${GEM_PATH};"
}

# If we don't have a distribution of common scripting
# languages already, then set one up
if [[ ! -f "${LANG_RT_PATH}/done-stamp" ]] ; then
    polysquare_task "Installing language runtimes" \
        polysquare_install_language_runtimes
else
    polysquare_task "Restoring language runtimes from cache" \
        polysquare_restore_language_runtimes_from_cache
fi

# Activate languages
polysquare_task "Activating languages" polysquare_activate_languages
