#!/usr/bin/env bash
# /tests/polysquare_project_helper.bash
#
# Copies the sample project into a temporary directory and changes into
# it, running the generic setup script.
#
# See LICENCE.md for Copyright information

load polysquare_project_copy_helper
load polysquare_container_generate_helper

function polysquare_project_setup {
    polysquare_generate_container_setup \
        project polysquare_setup_and_teardown_example_project
    polysquare_project_copy_setup python
}

function polysquare_project_teardown {
    polysquare_project_copy_teardown
    polysquare_generate_container_teardown
}
