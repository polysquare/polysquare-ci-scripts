#!/usr/bin/env bash
# /travis/setup/shell/setup.sh
#
# Travis CI Script which sets up an environment to test and check
# shell scripts. The standard output of this script should be
# evaluated directly, as it will cause environment variables to be set,
# for example:
#
#     eval $(curl -LSs path/to/setup.sh | bash)
#
# See LICENCE.md for Copyright information

# Sets up some common functions, and then prints them to stdout, so
# that other scripts can use them later and we can use them here.
if [ -z "${__POLYSQUARE_CI_SCRIPTS_BOOTSTRAP+x}" ] ; then
    BOOT="$(curl -LSs public-travis-scripts.polysquare.org/bootstrap.sh | bash)"
else
    bootstrap_dir=$(dirname "${__POLYSQUARE_CI_SCRIPTS_BOOTSTRAP}")
    BOOT=$(bash "${bootstrap_dir}/bootstrap.sh")
fi

eval "${BOOT}" && echo "${BOOT}"

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

polysquare_fetch_and_fwd "setup/project/language.sh" \
    -l haskell \
    -l python \
    -l ruby \
    -d "${CONTAINER_DIR}"
polysquare_fetch_and_exec "setup/project/project.sh"

polysquare_fetch "check/project/check.sh"
polysquare_fetch "check/project/lint.sh"
polysquare_fetch "check/shell/check.sh"
polysquare_fetch "check/shell/lint.sh"
polysquare_fetch "check/shell/test.sh"

polysquare_print_task "Installing shell testing utilities"

polysquare_print_status "Installing shell linters"
polysquare_fatal_error_on_failure npm install -g bat-fork
polysquare_fatal_error_on_failure pip install bashlint
polysquare_fatal_error_on_failure cabal install shellcheck

polysquare_task_completed
