#!/usr/bin/env bash
# /travis/setup/project/project.sh
#
# Travis CI Script to set up project level linters. This script
# assumes that a working and containerized installation of
# both ruby and python are available. If they aren't, consider
# running the setup/language.sh script first to install them.
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

function polysquare_set_up_project_linters {
    polysquare_task "Installing markdownlint" 
        polysquare_fatal_error_on_failure gem install \
            --user-install --conservative --no-ri --no-rdoc mdl
    polysquare_task "Installing polysquare style guide linter" \
        polysquare_fatal_error_on_failure pip install \
            polysquare-generic-file-linter
}

polysquare_task "Setting up project linters" polysquare_set_up_project_linters
