#!/bin/bash
# /travis/python-prepare-doc-deploy.sh
#
# Sets environment variables so that deploys with markdown documentation
# work correctly. Use with source on before_deploy.
#
# See LICENCE.md for Copyright information

export PATH=${HOME}/.cabal/bin:${PATH}
