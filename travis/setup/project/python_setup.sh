#!/usr/bin/env bash
# /travis/setup/project/python_setup.sh
#
# Travis CI script to set up a self-contained instance of python-build
# and separate python installations. The output of this script should be
# evaluated directly, for instance
#
#     eval $(curl -LSs http://path/to/setup/project/setup_python.sh | bash)
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

while getopts "d:v:" opt "$@"; do
    case "$opt" in
    d) container_dir="$OPTARG"
       ;;
    v) python_version="$OPTARG"
       ;;
    esac
done

python_container_dir="${container_dir}/_languages/python"
python_build_dir="${python_container_dir}/python-build/"

function polysquare_setup_python {
    mkdir -p "${python_container_dir}"

    function polysquare_setup_python_build {
        # Set up a python-build installation. We need to:
        # 1. Clone pyenv
        # 2. Run the pyenv/plugins/python-build/install.sh script        
        local _work_dir

        mkdir -p "${python_build_dir}"
        _work_dir=$(mktemp -d "${python_build_dir}/t.XXXXXX")

        pushd "${_work_dir}" > /dev/null 2>&1
        polysquare_task "Downloading pyenv" \
            polysquare_fatal_error_on_failure \
                git clone git://github.com/yyuu/pyenv
        polysquare_task "Installing python-build" \
            polysquare_fatal_error_on_failure \
                PREFIX="${python_build_dir}" \
                    "${_work_dir}/pyenv/plugins/python-build/install.sh"
        popd > /dev/null 2>&1
        polysquare_fatal_error_on_failure rm -rf "${_work_dir}"
    }

    function polysquare_install_python {
        # Install a python version. This will require us to:
        # 1. Put python-build in our PATH
        # 2. Use python-build to install the nominated python version
        #
        # This command will fail if the nominated python version cannot be
        # installed on the target platform (either because it doesn't exist or
        # or for some other reason).
        local build_path="${container_dir}/_cache/python/${python_version}"
        local download_cache="${container_dir}/_cache/python/download"
        local py_ver_cont="${python_container_dir}/${python_version}"

        mkdir -p "${build_path}"

        export PATH="${python_build_dir}/bin:${PATH}"
        export PYTHONDONTWRITEBYTECODE=1
        polysquare_fatal_error_on_failure which python-build

        polysquare_fatal_error_on_failure \
            PYTHON_BUILD_CACHE_PATH="${download_cache}" \
                PYTHON_BUILD_BUILD_PATH="${build_path}" \
                    python-build --keep "${python_version}" \
                        "${py_ver_cont}"
        
        # Get rid of a bunch of things which we don't need
        python_path=$(echo "${py_ver_cont}"/lib/python*)

        # Unit tests and test data (~40MB)
        find "${python_path}" -type d -name "test" -execdir rm -rf {} \; \
            2>/dev/null

        # Compiled python objects
        find "${python_path}" -type f -name "*.pyc" -execdir rm -rf {} \; \
            2>/dev/null
        find "${python_path}" -type f -name "*.pyo" -execdir rm -rf {} \; \
            2>/dev/null
    }

    function polysquare_activate_python {
        # There's only one python lib directory, so use a glob to find
        # out what it is
        local py_ver_cont="${python_container_dir}/${python_version}"
        local python_path

        python_path=$(echo "${py_ver_cont}"/lib/python*)

        echo "export PATH=${py_ver_cont}/bin:\${PATH};"
        echo "export PYTHONPATH=${python_path}/site-packages;"
        echo "export PYTHONDONTWRITEBYTECODE=1;"
        echo "export VIRTUAL_ENV=${py_ver_cont};"
        echo "export POLYSQUARE_PYTHON_ACTIVE_VERSION=${python_version};"
        echo "export POLYSQUARE_PYTHON_ACTIVE_CONTAINER=${py_ver_cont};"
    }

    if ! [ -d "${python_build_dir}" ] ; then
        polysquare_task "Installing python-build" polysquare_setup_python_build
    fi

    if ! [ -d "${python_container_dir}/${python_version}" ] ; then
        polysquare_task "Installing python version ${python_version}" \
            polysquare_install_python
    fi

    polysquare_task "Activating python version ${python_version}" \
        polysquare_activate_python
}

polysquare_task "Setting up python" polysquare_setup_python
polysquare_exit_with_failure_on_script_failures
