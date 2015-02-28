#!/bin/bash
# /travis/prepare-lang-cache.sh
#
# Copies locally installed packages into cache container, where they will be
# restored from later. Also deletes useless build artefacts which only
# take up space.
#
# As a result, to install more packages, the caches need to be flushed
# completely first.
#
# See LICENCE.md for Copyright information

while getopts "d:l:" opt; do
    case "$opt" in
    d) container_dir=$OPTARG
       ;;
    l) languages+=" $OPTARG"
       ;;
    esac
done

echo "=> Preparing for language caching."

LANG_RT_PATH="${container_dir}/_languages"

python_dirs="" # shellcheck disable=SC2034
ruby_dirs="gem" # shellcheck disable=SC2034
haskell_dirs="ghc cabal" # shellcheck disable=SC2034
node_dirs="" # shellcheck disable=SC2034

echo "   ... Copying local installation directories to cache container."

for lang in ${languages} ; do
    dirs_variable="${lang}_dirs"
    for dir in ${!dirs_variable} ; do
        cp -TRf "${HOME}/.${dir}" "${LANG_RT_PATH}/.${dir}"
    done
done

echo "   ... Cleaning up artefacts"

if [ -d "${LANG_RT_PATH}/.cabal" ] ; then
    cabal_lib="${LANG_RT_PATH}/.cabal/lib"
    find "${cabal_lib}" -type f -name "*.a" -execdir rm -f ";" 2>/dev/null
    find "${cabal_lib}" -type f -name "*.o" -execdir rm -f ";" 2>/dev/null
    find "${LANG_RT_PATH}/.cabal/packages" -type f \
        -name "*.tar.gz" -execdir rm -f ";" 2>/dev/null
fi

# Clean out compiled python files, wherever they are within LANG_RT_PATH
if [ -d "${LANG_RT_PATH}" ] ; then
    find "${LANG_RT_PATH}" -type f -name "*.pyc" -execdir rm -f ";" 2>/dev/null
    find "${LANG_RT_PATH}" -type d -name "__pycache__" -execdir \
        rm -rf ";" 2>/dev/null
fi

# Reset timestamp on all package.json files, whose timestamps are always updated
# on each run on npm install
if [ -d "${LANG_RT_PATH}/node" ] ; then
    cmd="find ${LANG_RT_PATH}/node -type f -name \"package.json\""
    package_json_files=$(eval "${cmd}")
    for file in ${package_json_files} ; do
        touch -mt 0001010000 "${file}"
    done
fi

echo "   ... To install other packages in this container, delete the"\
    "build cache first."

