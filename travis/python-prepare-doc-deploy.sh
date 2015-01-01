#!/bin/bash
# /travis/python-prepare-doc-deploy.sh
#
# Symlinks everything inside ~/.cabal/bin to $VIRTUAL_ENV/bin,
# which enables the use of pandoc at deploy-time. Environment
# variables aren't preserved at the deploy step, hence why this
# approach is needed here.
#
# See LICENCE.md for Copyright information

for file in ${HOME}/.cabal/bin/* ; do
    ln -s "${HOME}/.cabal/bin/${file}" "${VIRTUAL_ENV}/bin/"
done
