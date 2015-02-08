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

polysquare_print_task "Setting up project linters"
polysquare_print_status "Installing markdownlint"
polysquare_fatal_error_on_failure gem install mdl
polysquare_print_status "Installing polysquare style guide linter"
polysquare_fatal_error_on_failure pip install polysquare-generic-file-linter
