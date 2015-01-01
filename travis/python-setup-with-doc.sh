#!/bin/bash
# /travis/python-setup-with-doc.sh
#
# A wrapper around setup-lang.sh to setup markdown documentation
# support for python packages.
#
# This script should be invoked with source.
#
# See LICENCE.md for Copyright information

wget public-travis-scripts.polysquare.org/setup-lang.sh > /dev/null 2>&1
wget public-travis-scripts.polysquare.org/python-install.sh > /dev/null 2>&1
wget public-travis-scripts.polysquare.org/python-prepare-doc-deploy.sh > /dev/null 2>&1
source setup-lang.sh -l haskell -p ~/virtualenv
bash python-install.sh -p
