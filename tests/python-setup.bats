#!/usr/bin/env bats
# /tests/python-setup.bats
#
# Tests for setup/shell/python.sh - checking to make sure certain utilities
# are installed after the python setup script has been run.
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
load polysquare_container_copy_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/util.sh"

bootstrap="${POLYSQUARE_TRAVIS_SCRIPTS}/bootstrap.sh"
python_sample_project="${POLYSQUARE_TRAVIS_SCRIPTS}/../sample/python"

function python_setup {
    cd "${python_sample_project}"
    local container="${CONTAINER_DIR}"
    local boot=$(bash "${bootstrap}" -d "${container}" -s setup/python/setup.sh)
    eval "${boot}"
}

@test "Prospector is available after running python setup script" {
    python_setup

    which prospector
}

@test "Pylint is available after running python setup script" {
    python_setup

    which pylint
}

@test "Dodgy is available after running python setup script" {
    python_setup

    which dodgy
}

@test "Frosted is available after running python setup script" {
    python_setup

    which frosted
}

@test "McCabe is available after running python setup script" {
    python_setup

    python -c "import mccabe"
}

@test "PEP257 is available after running python setup script" {
    python_setup

    which pep257
}

@test "PEP8 is available after running python setup script" {
    python_setup

    which pep8
}

@test "PyFlakes is available after running python setup script" {
    python_setup

    which pyflakes
}

@test "PyRoma is available after running python setup script" {
    python_setup

    which pyroma
}

@test "Vulture is available after running python setup script" {
    python_setup

    which vulture
}

@test "PyChecker is available after running python setup script" {
    python_setup

    which pychecker
}

@test "Flake8 is available after running python setup script" {
    python_setup

    which flake8
}

@test "PEP257 plugin for flake8 is installed" {
    python_setup

    flake8 --version | grep pep257
}

@test "Blind-Except plugin for flake8 is installed" {
    python_setup

    flake8 --version | grep flake8-blind-except
}

@test "Double-quotes plugin for flake8 is installed" {
    python_setup

    flake8 --version | grep flake8-double-quotes
}

@test "Blind-Except plugin for flake8 is installed" {
    python_setup

    flake8 --version | grep flake8-blind-except
}

@test "Import order plugin for flake8 is installed" {
    python_setup

    flake8 --version | grep import-order
}

@test "TODO plugin for flake8 is installed" {
    python_setup

    flake8 --version | grep flake8-todo
}
