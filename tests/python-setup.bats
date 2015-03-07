#!/usr/bin/env bats
# /tests/python-setup.bats
#
# Tests for setup/shell/python.sh - checking to make sure certain utilities
# are installed after the python setup script has been run.
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
load polysquare_container_copy_helper
load polysquare_python_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/util.sh"

setup() {
    polysquare_python_setup
    polysquare_container_copy_setup
}

teardown() {
    polysquare_container_copy_teardown
    polysquare_python_teardown
}

@test "Prospector is available after running python setup script" {
    which prospector
}

@test "Pylint is available after running python setup script" {
    which pylint
}

@test "Dodgy is available after running python setup script" {
    which dodgy
}

@test "Frosted is available after running python setup script" {
    which frosted
}

@test "McCabe is available after running python setup script" {
    python -c "import mccabe"
}

@test "PEP257 is available after running python setup script" {
    which pep257
}

@test "PEP8 is available after running python setup script" {
    which pep8
}

@test "PyFlakes is available after running python setup script" {
    which pyflakes
}

@test "PyRoma is available after running python setup script" {
    which pyroma
}

@test "Vulture is available after running python setup script" {
    which vulture
}

@test "PyChecker is available after running python setup script" {
    which pychecker
}

@test "Flake8 is available after running python setup script" {
    which flake8
}

@test "PEP257 plugin for flake8 is installed" {
    flake8 --version | grep pep257
}

@test "Blind-Except plugin for flake8 is installed" {
    flake8 --version | grep flake8-blind-except
}

@test "Double-quotes plugin for flake8 is installed" {
    flake8 --version | grep flake8-double-quotes
}

@test "Blind-Except plugin for flake8 is installed" {
    flake8 --version | grep flake8-blind-except
}

@test "Import order plugin for flake8 is installed" {
    flake8 --version | grep import-order
}

@test "TODO plugin for flake8 is installed" {
    flake8 --version | grep flake8-todo
}
