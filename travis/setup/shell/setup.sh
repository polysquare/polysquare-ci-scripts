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

polysquare_fetch_and_source "python-util.sh"
polysquare_fetch_and_source "haskell-util.sh"

# Set up some programming languages our tools are written in.
polysquare_fetch_and_fwd "setup/project/haskell_setup.sh" \
    -d "${CONTAINER_DIR}" \
    -v 7.8.4

polysquare_fetch_and_fwd "setup/project/python_setup.sh" \
    -d "${CONTAINER_DIR}" \
    -v 2.7

polysquare_fetch_and_fwd "setup/project/ruby_setup.sh" \
    -d "${CONTAINER_DIR}" \
    -v 1.9.3-p551

polysquare_fetch_and_fwd "setup/project/node_setup.sh" \
    -d "${CONTAINER_DIR}" \
    -v 0.12.0

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

    polysquare_fatal_error_on_failure \
        gem install --conservative --no-ri --no-rdoc bundler simplecov

    # Clone local fork of bashcov and install it from there
    local bashcov_working_dir="${CONTAINER_DIR}/_cache/bashcov_working_dir"
    mkdir -p "${bashcov_working_dir}" > /dev/null 2>&1
    pushd "${bashcov_working_dir}" > /dev/null 2>&1
    polysquare_fatal_error_on_failure git clone \
        git://github.com/smspillaz/bashcov
    pushd bashcov > /dev/null 2>&1
    polysquare_fatal_error_on_failure bundle install
    polysquare_fatal_error_on_failure rake install
    popd > /dev/null 2>&1
    popd > /dev/null 2>&1

    rm -rf "${bashcov_working_dir}" > /dev/null 2>&1
}

function polysquare_install_shell_linting_utils {
    polysquare_fatal_error_on_failure \
        polysquare_run_if_unavailable bashlint \
            polysquare_pip_install bashlint
    polysquare_run_if_unavailable shellcheck \
        polysquare_cabal_install_binary shellcheck
}

polysquare_task "Installing shell testing utilities" \
    polysquare_install_shell_testing_utils
polysquare_task "Installing shell linting utilities" \
    polysquare_install_shell_linting_utils
