#!/usr/bin/env bash
# /travis/setup-local-languages.sh
#
# Travis CI script to set up self-contained versions of
# scripting languages and their packaging systems. This
# script should be passed to the bash "source" command.
#
# See LICENCE.md for Copyright information

LANG_RT_PATH=$1

function setup_haskell {
    echo "=> Setting up Haskell..."
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

    apt-get download ghc cabal-install > /dev/null
    echo "   ... Packages downloaded"
    find . -maxdepth 1 -type f -name "*.deb" -print0 | \
        xargs -L 1 -0 -I {} dpkg-deb --extract {} "${LANG_RT_PATH}"
    rm ./*.deb
    echo "   ... Packages extracted"    

    rm "${LANG_RT_PATH}/usr/lib/ghc/package.conf.d"
    ln -s "${LANG_RT_PATH}/var/lib/ghc/package.conf.d" \
        "${LANG_RT_PATH}/usr/lib/ghc/package.conf.d"

    for filename in ghc ghci ghc-pkg haddock-ghc-7.4.1 hsc2hs runghc ; do
        sed -i "s:/usr:${LANG_RT_PATH}/usr:" \
            "${LANG_RT_PATH}/usr/bin/${filename}"
        sed -i "s:/var:${LANG_RT_PATH}/var:" \
            "${LANG_RT_PATH}/usr/bin/${filename}"
    done

    find "${LANG_RT_PATH}/var/lib/ghc/package.conf.d" \
        -name "*.conf" -type f -print0 | \
            xargs -L 1 -0 sed -i "s:/usr:${LANG_RT_PATH}/usr:"

    ln -s /usr/lib/x86_64-linux-gnu/libgmp.so.10 \
        "${LANG_RT_PATH}/usr/lib/ghc/libgmp.so"
    ln -s /usr/lib/x86_64-linux-gnu/libgmp.so.10 \
        "${LANG_RT_PATH}/usr/lib/libgmp.so"
    ln -s /usr/lib/x86_64-linux-gnu/libffi.so.6 \
        "${LANG_RT_PATH}/usr/lib/ghc/libffi.so"
    ln -s /usr/lib/x86_64-linux-gnu/libffi.so.6 \
        "${LANG_RT_PATH}/usr/lib/libffi.so"
    echo "   ... Package paths adjusted"

    mkdir -p "${LANG_RT_PATH}/cabal"
    mkdir -p "${LANG_RT_PATH}/ghc"

    ghc-pkg recache > /dev/null
    echo "   ... GHC package cache up to date"
    echo "   ... done!"
}

function setup_python {
    echo "=> Setting up Python"

    python_prefix="lib/python2.7/site-packages"
    next_pythonpath="${LANG_RT_PATH}/usr/${python_prefix}"

    mkdir -p "${next_pythonpath}"

    export PYTHONPATH="${next_pythonpath}":${PYTHONPATH}

    echo "   ... Installing virtualenv"
    easy_install --prefix "${LANG_RT_PATH}/usr/" virtualenv > /dev/null 2>&1

    echo "   ... Creating virtualenv"
    virtualenv --python=/usr/bin/python "${LANG_RT_PATH}/python" > /dev/null 2>&1
}

function setup_ruby {
    echo "=> Setting up Ruby"

    # We just symlink ~/.gem to ${LANG_RT_PATH}/gems, that way it can be backed
    # up and restored later
    mkdir -p "${LANG_RT_PATH}/gems"
}

echo "=> Setting up language runtimes in ${LANG_RT_PATH}"
export PATH=${LANG_RT_PATH}/usr/bin:${PATH}
export LD_LIBRARY_PATH=${LANG_RT_PATH}/usr/lib:${LD_LIBRARY_PATH}

# If we don't have a distribution of common scripting
# languages already, then set one up
if [[ ! -f "${LANG_RT_PATH}/done-stamp" ]] ; then
    echo "=> Installing language runtimes as they're not available in the cache"

    mkdir -p "${LANG_RT_PATH}"
    pushd "${LANG_RT_PATH}" > /dev/null

    setup_haskell
    setup_python
    setup_ruby

    echo "done" >> "${LANG_RT_PATH}/done-stamp"

    popd > /dev/null

else
    echo "=> Restoring language runtimes from cache"

    for local_dir in gem ghc cabal ; do
        mv "${LANG_RT_PATH}/.${local_dir}" "${HOME}/.${local_dir}" 
    done
fi

# Update package repositories (we should do this on every run)
echo "=> Updating scripting language repositories"
cabal update > /dev/null

# Activate languages
echo "=> Activating languages"
source "${LANG_RT_PATH}/python/bin/activate"
export PYTHON_SETUP_LOCALLY=1
export PATH=${HOME}/.gem/ruby/1.8/bin/:${PATH}
export PATH=${HOME}/.cabal/bin:${PATH}
