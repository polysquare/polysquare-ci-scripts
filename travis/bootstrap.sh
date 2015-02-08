#!/usr/bin/env bash
# /travis/bootstrap.sh
#
# Travis CI Script which downloads util.sh and sets up the script tree in
# CONTAINER_DIR. CONTAINER_DIR must be set in order to use this script. This
# script should be called directly from a project's "setup" script, whose
# output is evaluated later.
#
# This script will set the following environment variables:
# - POLYSQUARE_CI_SCRIPTS_DIR
#
# See LICENCE.md for Copyright information

# This environment variable must be set. If it is not set, then error out
# immediately.
if [ -z "${CONTAINER_DIR+x}" ] ; then
    >&2 echo "CONTAINER_DIR must be set before these scripts can be used."
    >&2 echo "Call export CONTAINER_DIR=... or specify it in the environment."
    exit 1
fi

# If this variable is specified, then there's no need to redownload util.sh,
# so don't redownload it.
if [ -z "${__POLYSQUARE_CI_SCRIPTS_BOOTSTRAP+x}" ] ; then

    >&2 mkdir -p "${POLYSQUARE_CI_SCRIPTS_DIR}"
    >&2 curl -LSs "public-travis-scripts.polysquare.org/travis/util.sh" \
        -O "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"
    
    POLYSQUARE_CI_SCRIPTS_DIR="${CONTAINER_DIR}/_scripts"

else

    POLYSQUARE_CI_SCRIPTS_DIR=$(dirname "${__POLYSQUARE_CI_SCRIPTS_BOOTSTRAP}")

fi

echo "export POLYSQUARE_CI_SCRIPTS_DIR=${POLYSQUARE_CI_SCRIPTS_DIR}"
echo "source ${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"
