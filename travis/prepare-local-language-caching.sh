#!/bin/bash
# /travis/prepare-local-language-caching.sh
#
# Copies locally installed packages into ~/.install, where they will be
# restored from later
#
# See LICENCE.md for Copyright information

LANG_RT_PATH=$1

for local_dir in gem ghc cabal ; do
    mv "${HOME}/.${local_dir}" "${LANG_RT_PATH}/.${local_dir}"
done
