#!/usr/bin/env bash
# /travis/bootstrap.sh
#
# Travis CI Script which downloads util.sh and sets up the script tree in
# the directory specified by -d. This script should be called with both -d and
# -s, -s being a relative path from public-travis-scripts.polysquare.org to
# a setup script which will set everything up once this command has finished
# running.
#
# This script will set the following environment variables:
# - POLYSQUARE_CI_SCRIPTS_DIR
#
# See LICENCE.md for Copyright information

while getopts "d:s:" opt "$@"; do
    case "$opt" in
    d) container_dir="$OPTARG"
       ;;
    s) setup_script="$OPTARG"
       ;;
    esac
done

: ${container_dir?"Must pass a path to a container with -d"}
: ${setup_script?"Must pass the path to a setup script with -s"}

>&2 mkdir -p "${container_dir}"

# Download and install polysquare_indent
if ! [ -f "${container_dir}/shell/bin/polysquare_indent" ] ; then
    progs_base="http://public-travis-programs.polysquare.org"

    >&2 mkdir -p "${container_dir}/shell"
    >&2 mkdir -p "${container_dir}/shell/bin"

    >&2 curl -LSs "${progs_base}/polysquare_indent" -o \
        "${container_dir}/shell/bin/polysquare_indent"
    >&2 chmod +x "${container_dir}/shell/bin/polysquare_indent"
fi

# If this variable is specified, then there's no need to redownload util.sh
# so don't download it
if [ -z "${__POLYSQUARE_CI_SCRIPTS_BOOTSTRAP+x}" ] ; then
    >&2 mkdir -p "${POLYSQUARE_CI_SCRIPTS_DIR}"
    >&2 curl -LSs "public-travis-scripts.polysquare.org/travis/util.sh" \
        -O "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"
    
    POLYSQUARE_CI_SCRIPTS_DIR="${container_dir}/_scripts"
else
    POLYSQUARE_CI_SCRIPTS_DIR=$(dirname "${__POLYSQUARE_CI_SCRIPTS_BOOTSTRAP}")
fi

function eval_and_fwd {
    eval "$1" && echo "$1"
}

eval_and_fwd "export CONTAINER_DIR=${container_dir}"
eval_and_fwd "export PATH=${CONTAINER_DIR}/shell/bin/:\${PATH}"
eval_and_fwd "export POLYSQUARE_CI_SCRIPTS_DIR=${POLYSQUARE_CI_SCRIPTS_DIR}"
eval_and_fwd "source ${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

# Now that we've set everything up, pass control to our setup script (remember
# that bash 4.3 is now in our PATH).
if [ -z "${__POLYSQUARE_CI_SCRIPTS_BOOTSTRAP+x}" ] ; then
    curl -LSs "public-travis-scripts.polysquare.org/${setup_script}" | bash
else
    cat "${POLYSQUARE_CI_SCRIPTS_DIR}/${setup_script}" | bash
fi
