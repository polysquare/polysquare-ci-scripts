#!/usr/bin/env bash
# /tests/polysquare_project_helper.bash
#
# Copies the sample project into a temporary directory and changes into
# it, running the generic setup script.
#
# See LICENCE.md for Copyright information

load polysquare_project_copy_helper

function polysquare_project_setup {
    polysquare_project_copy_setup project
}

function polysquare_project_teardown {
    polysquare_project_copy_teardown
}
