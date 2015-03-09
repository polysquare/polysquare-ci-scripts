#!/usr/bin/env bash
# /tests/polysquare_python_helper.bash
#
# Copies the python sample project into a temporary directory and changes into
# it, running the python setup script.
#
# See LICENCE.md for Copyright information

load polysquare_project_copy_helper
load polysquare_container_generate_helper

function polysquare_python_setup {
    polysquare_generate_container_setup \
        python polysquare_setup_and_teardown_example_project
    polysquare_project_copy_setup python
}

function polysquare_python_teardown {
    polysquare_project_copy_teardown
    polysquare_generate_container_teardown
}
