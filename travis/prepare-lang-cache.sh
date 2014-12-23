#!/bin/bash
# /travis/prepare-lang-cache.sh
#
# Copies locally installed packages into cache path, where they will be
# restored from later
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

LANG_RT_PATH="${path}"

python_dirs="" # shellcheck disable=SC2034
ruby_dirs="gem" # shellcheck disable=SC2034
haskell_dirs="ghc cabal" # shellcheck disable=SC2034

for lang in ${languages} ; do
    dirs_variable="${lang}_dirs"
    for dir in ${!dirs_variable} ; do
        mv "${HOME}/.${dir}" "${LANG_RT_PATH}/.${dir}"
    done
done
