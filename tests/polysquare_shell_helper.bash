#!/usr/bin/env bash
# /tests/polysquare_shell_helper.bash
#
# Copies the shell sample project into a temporary directory and changes into
# it, running the shell setup script.
#
# See LICENCE.md for Copyright information

load polysquare_project_copy_helper
load polysquare_container_generate_helper

function polysquare_shell_setup {
    polysquare_generate_container_setup \
        shell polysquare_setup_and_teardown_example_project
    polysquare_project_copy_setup shell
}

function polysquare_shell_teardown {
    polysquare_project_copy_teardown
    polysquare_generate_container_teardown
}
