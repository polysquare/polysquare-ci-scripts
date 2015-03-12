#!/usr/bin/env bash
# /travis/setup/project/ruby_setup.sh
#
# Travis CI script to set up a self-contained instance of rvm-download
# and separate ruby installations. The output of this script should be
# evaluated directly, for instance
#
#     eval $(curl -LSs http://path/to/setup/project/setup_ruby.sh | bash)
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

while getopts "d:v:" opt "$@"; do
    case "$opt" in
    d) container_dir="$OPTARG"
       ;;
    v) ruby_version="$OPTARG"
       ;;
    esac
done

ruby_container_dir="${container_dir}/_languages/ruby"
rvm_download_dir="${ruby_container_dir}/rvm-download"

function polysquare_setup_ruby {
    mkdir -p "${ruby_container_dir}"

    function polysquare_setup_rvm_download {
        # Set up a ruby-build and chruby installation. We need to:
        # 1. Clone rvm-download
        # 2. Run the pyenv/plugins/ruby-build/install.sh script        

        mkdir -p "${rvm_download_dir}"
        polysquare_fatal_error_on_failure \
            git clone https://github.com/garnieretienne/rvm-download.git \
                "${rvm_download_dir}"
    }

    function polysquare_install_ruby {
        # Install a ruby version. This will require us to:
        # 1. Put ruby-install in our PATH
        # 2. Use ruby-install to install the nominated ruby version
        #
        # This command will fail if the nominated ruby version cannot be
        # installed on the target platform (either because it doesn't exist or
        # or for some other reason).

        mkdir -p "${ruby_container_dir}/versions"

        export PATH="${rvm_download_dir}/bin:${PATH}"
        polysquare_fatal_error_on_failure which rbenv-download

        polysquare_fatal_error_on_failure \
            RBENV_ROOT="${ruby_container_dir}" rbenv-download "${ruby_version}"
    }

    function polysquare_activate_ruby {
        # There's only one ruby lib directory, so use a glob to find
        # out what it is
        local rb_cont="${ruby_container_dir}/versions"
        local rb_ver_cont="${rb_cont}/${ruby_version}"
        local rb_short_ver="${ruby_version%%-*}"
        
        if [[ "${rb_short_ver}" =~ ^.*1.9.*$ ]] ; then
            rb_short_ver="1.9.1"
        fi
        
        local rb_sys_gem="${rb_ver_cont}/lib/${ruby_version%%-*}"
        local rb_site_gem="${rb_ver_cont}/lib/site_ruby/${ruby_version%%-*}"
        local rb_home_gem="${rb_ver_cont}"

        echo "export PATH=${rb_ver_cont}/bin:\${PATH};"
        echo "export GEM_PATH=${rb_home_gem}:${rb_site_gem}:${rb_sys_gem};"
        echo "export GEM_HOME=${rb_home_gem};"
        echo "export POLYSQUARE_RUBY_ACTIVE_VERSION=${ruby_version};"
        echo "export POLYSQUARE_RUBY_ACTIVE_CONTAINER=${rb_ver_cont};"
    }

    if ! [ -d "${rvm_download_dir}" ] ; then
        polysquare_task "Installing RVM-Download" polysquare_setup_rvm_download
    fi

    if ! [ -d "${ruby_container_dir}/${ruby_version}" ] ; then
        polysquare_task "Installing ruby version ${ruby_version}" \
            polysquare_install_ruby
    fi

    polysquare_task "Activating ruby version ${ruby_version}" \
        polysquare_activate_ruby
}

polysquare_task "Setting up ruby" polysquare_setup_ruby
polysquare_exit_with_failure_on_script_failures
