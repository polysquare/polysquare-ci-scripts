#!/usr/bin/env bash
# /travis/setup/shell/setup.sh
#
# Travis CI Script which sets up an environment to test and check
# shell scripts. The standard output of this script should be
# evaluated directly, as it will cause environment variables to be set,
# for example:polysquare_pip_install
#
#     eval $(curl -LSs path/to/setup.sh | bash)
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"
source "${POLYSQUARE_CI_SCRIPTS_DIR}/python-util.sh"

polysquare_fetch_and_fwd "setup/project/language.sh" \
    -l haskell \
    -l python \
    -l ruby \
    -l node \
    -d "${CONTAINER_DIR}"
polysquare_fetch_and_exec "setup/project/project.sh"

polysquare_fetch "check/project/check.sh"
polysquare_fetch "check/project/lint.sh"
polysquare_fetch "check/shell/check.sh"
polysquare_fetch "check/shell/lint.sh"
polysquare_fetch "check/shell/test.sh"

function polysquare_install_shell_testing_utils {
    polysquare_fatal_error_on_failure \
        polysquare_run_if_unavailable bats \
            npm install -g bat-fork
}

function polysquare_install_shell_linting_utils {
    polysquare_fatal_error_on_failure \
        polysquare_run_if_unavailable bashlint \
            polysquare_pip_install bashlint
    polysquare_fatal_error_on_failure \
        polysquare_run_if_unavailable shellcheck \
            cabal install shellcheck
}

polysquare_task "Installing shell testing utilities" \
    polysquare_install_shell_testing_utils
polysquare_task "Installing shell linting utilities" \
    polysquare_install_shell_linting_utils
