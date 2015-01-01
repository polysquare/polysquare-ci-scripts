#!/bin/bash
# /travis/python-test-module.sh
#
# Downloads scripts common to all polysquare python projects and run
# tests and linters. The MODULE environment variable must be set.
#
# See LICENCE.md for Copyright information

set -e

wget public-travis-scripts.polysquare.org/prepare-lang-cache.sh
wget public-travis-scripts.polysquare.org/python-lint.sh
wget public-travis-scripts.polysquare.org/python-tests.sh
wget public-travis-scripts.polysquare.org/project-lint.sh

bash project-lint.sh -d . -e py
bash python-lint.sh -m "${MODULE}"
bash python-tests.sh -m "${MODULE}"
bash prepare-lang-cache.sh -l haskell -p ~/virtualenv
