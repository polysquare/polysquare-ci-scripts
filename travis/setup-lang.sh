#!/usr/bin/env bash
# /travis/setup-lang.sh
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

python_version=2.7

while getopts "d:l:s:" opt; do
    case "$opt" in
    d) container_dir=$OPTARG
       ;;
    l) languages+=" $OPTARG"
       ;;
    s) python_version=$OPTARG
       ;;
    esac
done

LANG_RT_PATH="${container_dir}/_languages"

# This script is special - its normal output will actually be another
# shell script, and all "normal" messages go to the standard error. Use
# echoerr whenever you want to print something.
function echoerr {
    >&2 echo "$@"
}

function suppress_output {
    output_file=$(mktemp /tmp/tmp.XXXXXXX)
    eval "$@" > "${output_file}" 2>&1
    command_result=$?
    if [ "${command_result}" != 0 ] ; then
        concat_cmd=$(echo "$@" | xargs echo)
        echoerr "Command ${concat_cmd} failed with ${command_result}"
        >&2 cat "${output_file}"
        exit "${command_result}"
    fi
}

function setup_haskell {
    echoerr "=> Setting up Haskell..."
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

    suppress_output apt-get download ghc cabal-install
    echoerr "   ... Packages downloaded"

    # These find commands are the exception to suppress_output -
    # they use pipes, so we need to use shell redirection instead.
    find . -maxdepth 1 -type f -name "*.deb" -print0 | \
        xargs -L 1 -0 -I {} dpkg-deb --extract {} "${LANG_RT_PATH}" 2>&1
    suppress_output rm ./*.deb
    echoerr "   ... Packages extracted"

    suppress_output rm "${LANG_RT_PATH}/usr/lib/ghc/package.conf.d"
    suppress_output ln -s "${LANG_RT_PATH}/var/lib/ghc/package.conf.d" \
        "${LANG_RT_PATH}/usr/lib/ghc/package.conf.d"

    for filename in ghc ghci ghc-pkg haddock-ghc-7.4.1 hsc2hs runghc ; do
        suppress_output sed -i "s:/usr:${LANG_RT_PATH}/usr:" \
            "${LANG_RT_PATH}/usr/bin/${filename}"
        suppress_output sed -i "s:/var:${LANG_RT_PATH}/var:" \
            "${LANG_RT_PATH}/usr/bin/${filename}"
    done

    find "${LANG_RT_PATH}/var/lib/ghc/package.conf.d" \
        -name "*.conf" -type f -print0 | \
            xargs -L 1 -0 sed -i "s:/usr:${LANG_RT_PATH}/usr:" 2>&1

    suppress_output ln -s /usr/lib/x86_64-linux-gnu/libgmp.so.10 \
        "${LANG_RT_PATH}/usr/lib/ghc/libgmp.so"
    suppress_output ln -s /usr/lib/x86_64-linux-gnu/libgmp.so.10 \
        "${LANG_RT_PATH}/usr/lib/libgmp.so"
    suppress_output ln -s /usr/lib/x86_64-linux-gnu/libffi.so.6 \
        "${LANG_RT_PATH}/usr/lib/ghc/libffi.so"
    suppress_output ln -s /usr/lib/x86_64-linux-gnu/libffi.so.6 \
        "${LANG_RT_PATH}/usr/lib/libffi.so"
    echoerr "   ... Package paths adjusted"

    suppress_output mkdir -p "${LANG_RT_PATH}/cabal"
    suppress_output mkdir -p "${LANG_RT_PATH}/ghc"

    # For the purposes of ghc-pkg we need to set PATH and LD_LIBRARY_PATH here
    export PATH=${LANG_RT_PATH}/usr/bin:${PATH}
    export LD_LIBRARY_PATH=${LANG_RT_PATH}/usr/lib:${LD_LIBRARY_PATH}

    suppress_output ghc-pkg recache
    echoerr "   ... GHC package cache up to date"
    echoerr "   ... Updating cabal repositories"
    suppress_output cabal update
    echoerr "   ... done!"

    suppress_output mkdir -p "${HOME}/.ghc"
    suppress_output mkdir -p "${HOME}/.cabal"
}

function setup_python {
    echoerr "=> Setting up Python"

    python_prefix="lib/python${python_version}/site-packages"
    next_pythonpath="${LANG_RT_PATH}/usr/${python_prefix}"

    suppress_output mkdir -p "${next_pythonpath}"

    echo "export PYTHONPATH=${next_pythonpath}:${PYTHONPATH};"

    # Having bytecode around is a waste of space and inflates the
    # build cache, so just disable it.
    echo "export PYTHONDONTWRITEBYTECODE=1;"

    # We need to export PYTHONPATH for the purposes of this script
    # too, so that easy_install and virtualenv do not fail
    export PYTHONPATH=${next_pythonpath}:${PYTHONPATH}

    echoerr "   ... Installing virtualenv"
    suppress_output easy_install --prefix "${LANG_RT_PATH}/usr/" virtualenv

    echoerr "   ... Creating virtualenv"
    suppress_output "${LANG_RT_PATH}/usr/bin/virtualenv" \
        "--python=/usr/bin/python${python_version}" "${LANG_RT_PATH}/python"
}

function setup_ruby {
    echoerr "=> Setting up Ruby"

    # We just symlink ~/.gem to ${LANG_RT_PATH}/gems, that way it can be backed
    # up and restored later
    suppress_output mkdir -p "${LANG_RT_PATH}/gems"
    suppress_output mkdir -p "${HOME}/.gem"
}

echoerr "=> Setting up language runtimes in ${LANG_RT_PATH}"

# If we don't have a distribution of common scripting
# languages already, then set one up
if [[ ! -f "${LANG_RT_PATH}/done-stamp" ]] ; then
    echoerr "=> Installing language runtimes as they're not available in the cache"

    suppress_output mkdir -p "${LANG_RT_PATH}"
    suppress_output pushd "${LANG_RT_PATH}"

    for language in ${languages} ; do

        eval "setup_${language}"

    done

    echo "done" >> "${LANG_RT_PATH}/done-stamp"

    suppress_output popd

else
    echoerr "=> Restoring language runtimes from cache"

    # These variables are not really unused - they're used, but only by
    # a compound statement, so shellcheck won't detect that.
    python_dirs="" # shellcheck disable=SC2034
    ruby_dirs="gem" # shellcheck disable=SC2034
    haskell_dirs="ghc cabal" # shellcheck disable=SC2034

    for lang in ${languages} ; do
        dirs_variable="${lang}_dirs"
        for dir in ${!dirs_variable} ; do
            suppress_output mv "${LANG_RT_PATH}/.${dir}" "${HOME}/.${dir}"
        done
    done
fi

# Activate languages
echoerr "=> Activating languages"

echo "export PATH=${LANG_RT_PATH}/usr/bin:\${PATH};"
echo "export PATH=${HOME}/.gem/ruby/1.8/bin/:\${PATH};"
echo "export PATH=${HOME}/.cabal/bin:\${PATH};"
echo "export PATH=${LANG_RT_PATH}/python/bin:\${PATH};"
echo "export LD_LIBRARY_PATH=${LANG_RT_PATH}/usr/lib:\${LD_LIBRARY_PATH};"
echo "export VIRTUAL_ENV=${LANG_RT_PATH}/python;"
echo "export PYTHON_SETUP_LOCALLY=1;"
