#!/bin/bash
# /travis/python-prepare-doc-deploy.sh
#
# Symlinks everything inside ~/.cabal/bin to $VIRTUAL_ENV/bin,
# which enables the use of pandoc at deploy-time. Environment
# variables aren't preserved at the deploy step, hence why this
# approach is needed here.
#
# See LICENCE.md for Copyright information

echo "=> Preparing for deployment with Markdown documentation."

while IFS= read -r -d '' path ; do
    file=$(basename "${path}")
    echo "   ... ${path} -> ${VIRTUAL_ENV}/bin/${file}"
    ln -s "${path}" "${VIRTUAL_ENV}/bin/${file}"
done < <(find "${HOME}/.cabal/bin" -type f -print0)
