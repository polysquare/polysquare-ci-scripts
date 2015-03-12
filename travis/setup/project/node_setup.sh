#!/usr/bin/env bash
# /travis/setup/project/node_setup.sh
#
# Travis CI script to set up a self-contained instance of nodeenv
# and separate node installations. The output of this script should be
# evaluated directly, for instance
#
#     eval $(curl -LSs http://path/to/setup/project/setup_node.sh | bash)
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

while getopts "d:v:" opt "$@"; do
    case "$opt" in
    d) container_dir="$OPTARG"
       ;;
    v) node_version="$OPTARG"
       ;;
    esac
done

node_container_dir="${container_dir}/_languages/node"
node_env_dir="${node_container_dir}/nodeenv"

function polysquare_setup_node {
    mkdir -p "${node_container_dir}"

    local node_ver_location="${node_container_dir}/${node_version}"

    function polysquare_install_nodeenv {
        # Set up PYTHONUSERBASE and install nodeenv
        polysquare_fatal_error_on_failure \
            PYTHONUSERBASE="${node_env_dir}" \
                easy_install --user nodeenv
    }

    function polysquare_install_node {
        # Set PYTHONPATH and use nodeenv to download a binary node for the
        # specified version
        local python_path=$(echo "${node_env_dir}"/lib/python*)
        
        polysquare_fatal_error_on_failure \
            PYTHONPATH="${python_path}/site-packages" \
                "${node_env_dir}"/bin/nodeenv \
                    --prebuilt --node="${node_version}" \
                        "${node_ver_location}"
        rm -rf "${node_ver_location}/src/"
        rm -rf "${node_ver_location}/lib/node_modules/npm/doc/"
        rm -rf "${node_ver_location}/lib/node_modules/npm/man/"
        rm -rf "${node_ver_location}/lib/node_modules/npm/html/"
    }

    function polysquare_activate_node {
        echo "export NPM_CONFIG_PREFIX=${node_ver_location};"
        echo "export NODE_PATH=${node_ver_location}/lib/node_modules;"
        echo "export PATH=${node_ver_location}/bin:\${PATH};"
        echo "export POLYSQUARE_NODE_ACTIVE_VERSION=${node_version};"
        echo "export POLYSQUARE_NODE_ACTIVE_CONTAINER=${node_ver_location};"
    }

    if ! [ -d "${node_env_dir}" ] ; then
        polysquare_task "Installing nodeenv" polysquare_install_nodeenv
    fi

    if ! [ -d "${node_ver_location}" ] ; then
        polysquare_task "Installing node version ${node_version}" \
            polysquare_install_node
    fi

    polysquare_task "Activating node version ${node_version}" \
        polysquare_activate_node
}

polysquare_task "Setting up node" polysquare_setup_node
polysquare_exit_with_failure_on_script_failures
