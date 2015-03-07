#!/usr/bin/env bash
# /travis/python-util.sh
#
# Travis CI Script which contains various utilities for
# for python related scripts, including python version checking.
#
# See LICENCE.md for Copyright information

function polysquare_get_python_version {
    local python_version_variable="$1"
    local _python_version=$(python --version 2>&1 | cut -d " " -f2 | head -n1)

    eval "${python_version_variable}='${_python_version}'"
}

function polysquare_python_is_pypy {
    local is_pypy_variable="$1"
    python --version 2>&1 | grep PyPy > /dev/null
    local is_pypy="$?"

    eval "${is_pypy_variable}='${is_pypy}'"
}

function polysquare_run_if_python_module_unavailable {
    python -c "import $1" > /dev/null 2>&1
    if [ "$?" -ne "0" ] ; then
        eval "${*:2}"
    fi
}

# Runs pip install with some pre-set options for caching
function polysquare_pip_install {
    pip install --cache-dir "${CONTAINER_DIR}/_languages/python/pip-cache" \
        -I "$@"
}
