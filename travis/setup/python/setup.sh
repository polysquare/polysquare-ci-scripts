#!/bin/bash
# /travis/setup/python/setup.sh
#
# Travis CI Script which sets up an environment to test and check
# python applications. The standard output of this script should be
# evaluated directly, as it will cause environment variables to be set,
# for example:
#
#     eval $(curl -LSs path/to/setup.sh | bash)
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"
polysquare_fetch_and_source "python-util.sh"

polysquare_fetch_and_fwd "setup/project/language.sh" \
    -l haskell \
    -l ruby \
    -d "${CONTAINER_DIR}"
polysquare_fetch_and_exec "setup/project/project.sh"

polysquare_fetch "check/project/check.sh"
polysquare_fetch "check/project/lint.sh"
polysquare_fetch "check/python/check.sh"
polysquare_fetch "check/python/lint.sh"
polysquare_fetch "check/python/prospector-config.yml"
polysquare_fetch "check/python/test.sh"
polysquare_fetch "check/python/coverage.sh"
polysquare_fetch "check/python/deploy.sh"
polysquare_fetch "check/python/install.sh"

function polysquare_install_python_dependencies {
    function polysquare_install_python_setup_dependencies {
        function polysquare_install_python_documentation_tools {
            polysquare_task "Installing pandoc" \
                polysquare_fatal_error_on_failure 
                    polysquare_run_if_unavailable pandoc \
                        cabal install pandoc
            polysquare_task "Installing python documentation converters" \
                polysquare_fatal_error_on_failure \
                    polysquare_run_if_python_module_unavailable \
                        setuptools_markdown \
                            polysquare_pip_install setuptools-markdown
        }

        polysquare_task "Installing setup documentation tools" \
            polysquare_install_python_documentation_tools
    }

    function polysquare_install_python_linters {
        local linters_to_install=(pylint
                                  pylint-common
                                  dodgy
                                  frosted
                                  mccabe
                                  pep257
                                  pep8
                                  pyflakes
                                  pyroma
                                  vulture
                                  git+https://github.com/landscapeio/prospector
                                  flake8
                                  flake8-blind-except
                                  flake8-docstrings
                                  flake8-double-quotes
                                  flake8-import-order
                                  flake8-todo)

        local python_version=""
        local is_pypy=""

        polysquare_get_python_version python_version
        polysquare_python_is_pypy is_pypy

        # Add pychecker as long as the current python version is less than
        # python3
        if [[ $(polysquare_numeric_version "${python_version}") < \
              $(polysquare_numeric_version "3.0.0") ]] &&
           [ -z "${is_pypy}" ]; then
            linters_to_install+=("http://sourceforge.net/projects/pychecker/files/pychecker/0.8.19/pychecker-0.8.19.tar.gz/download")
        fi

        local linters_space_separated="${linters_to_install[*]}"
        polysquare_fatal_error_on_failure \
            polysquare_run_if_unavailable prospector \
                polysquare_pip_install "${linters_space_separated}"
    }

    polysquare_task "Installing setup dependencies" \
        polysquare_install_python_setup_dependencies
    polysquare_task "Installing test dependencies" \
        polysquare_fatal_error_on_failure polysquare_pip_install -e ".[test]" \
            --process-dependency-links
    polysquare_task "Installing coverage tools" \
        polysquare_fatal_error_on_failure \
            polysquare_run_if_unavailable coverage \
                polysquare_pip_install coverage
    polysquare_task "Installing python linters" \
        polysquare_install_python_linters
}

polysquare_task "Installing python project dependencies" \
    polysquare_install_python_dependencies
