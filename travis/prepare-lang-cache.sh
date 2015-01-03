#!/bin/bash
# /travis/prepare-lang-cache.sh
#
# Copies locally installed packages into cache path, where they will be
# restored from later. Also deletes useless build artefacts which only
# take up space.
#
# As a result, to install more packages, the caches need to be flushed
# completely first.
#
# See LICENCE.md for Copyright information

while getopts "p:l:" opt; do
    case "$opt" in
    p) path=$OPTARG
       ;;
    l) languages+=" $OPTARG"
       ;;
    esac
done

echo "=> Preparing for language caching."

LANG_RT_PATH="${path}"

python_dirs="" # shellcheck disable=SC2034
ruby_dirs="gem" # shellcheck disable=SC2034
haskell_dirs="ghc cabal" # shellcheck disable=SC2034

echo "   ... Moving local installation directories to cache path."

for lang in ${languages} ; do
    dirs_variable="${lang}_dirs"
    for dir in ${!dirs_variable} ; do
        mv "${HOME}/.${dir}" "${LANG_RT_PATH}/.${dir}"
    done
done

echo "   ... Cleaning up haskell artefacts"

if [ -d "${LANG_RT_PATH}/.cabal" ] ; then
    cabal_lib="${LANG_RT_PATH}/.cabal/lib"
    find "${cabal_lib}" -type f -name "*.a" -execdir rm -f ";" 2>/dev/null
    find "${cabal_lib}" -type f -name "*.o" -execdir rm -f ";" 2>/dev/null
    find "${LANG_RT_PATH}/.cabal/packages" -type f \
        -name "*.tar.gz" -execdir rm -f ";" 2>/dev/null
fi

echo "   ... To install other packages in this container, delete the"\
    "build cache first."

