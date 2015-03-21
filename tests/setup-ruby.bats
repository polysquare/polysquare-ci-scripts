#!/usr/bin/env bats
# /tests/setup-ruby.bats
#
# Test setting up a self-contained ruby installation
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
load polysquare_fresh_container_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/util.sh"

setup() {
    polysquare_fresh_container_setup
}

teardown() {
    polysquare_fresh_container_teardown
}

@test "RVM-download is installed in container" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/ruby_setup.sh" -d \
        "${CONTAINER_DIR}"

    [ -f "${CONTAINER_DIR}/_languages/ruby/rvm-download/bin/rbenv-download" ]
}

@test "Can install ruby versions" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/ruby_setup.sh" -d \
        "${CONTAINER_DIR}" -v "2.0.0-p0"

    [ -f "${CONTAINER_DIR}/_languages/ruby/versions/2.0.0-p0/bin/ruby" ]
}

@test "Ruby 2.0.0-p0 installation has expected 2.0.0 lib directories" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/ruby_setup.sh" -d \
        "${CONTAINER_DIR}" -v "2.0.0-p0"

    local libdir="${CONTAINER_DIR}/_languages/ruby/versions/2.0.0-p0/lib/ruby"

    [ -d "${libdir}/site_ruby/2.0.0" ]
    [ -d "${libdir}/2.0.0" ]
}

@test "Ruby 2.0.0-p0 installation can be activated and has correct verison" {
    local setup="${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/ruby_setup.sh"
    local -r script=$(bash "${setup}" -d "${CONTAINER_DIR}" -v 2.0.0-p0)
    eval "${script}"

    which gem
    which ruby
    
    run ruby --version
    [[ "${output?}" =~ ^.*2.0.0p0.*$ ]]
}


@test "Ruby 1.9.3-p551 installation has expected 1.9.1 lib directories" {
    run bash "${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/ruby_setup.sh" -d \
        "${CONTAINER_DIR}" -v "1.9.3-p551"

    local libdir="${CONTAINER_DIR}/_languages/ruby/versions/1.9.3-p551/lib/ruby"

    [ -d "${libdir}/site_ruby/1.9.1" ]
    [ -d "${libdir}/1.9.1" ]
}

@test "Ruby 1.9.3-p551 installation can be activated and has correct verison" {
    local setup="${POLYSQUARE_TRAVIS_SCRIPTS}/setup/project/ruby_setup.sh"
    local -r script=$(bash "${setup}" -d "{CONTAINER_DIR}" -v 1.9.3-p551)
    eval "${script}"

    which gem
    which ruby
    
    run ruby --version
    [[ "${output?}" =~ ^.*1.9.3p551.*$ ]]
}


