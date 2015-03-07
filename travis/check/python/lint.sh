#!/usr/bin/env bash
# /travis/check/python/lint.sh
#
# Travis CI Script which lints python files, depends on having numerious
# python linters installed. Use setup/python/setup.sh to install them.
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"
source "${POLYSQUARE_CI_SCRIPTS_DIR}/python-util.sh"

while getopts "x:d:" opt; do
    case "$opt" in
    e) exclusions+=" $OPTARG"
       ;;
    esac
done

polysquare_python_check_dir="${POLYSQUARE_CI_SCRIPTS_DIR}/check/python/"
prospector_config="${polysquare_python_check_dir}/prospector-config.yml"


function polysquare_run_python_checkers {
    local is_pypy=""

    polysquare_get_python_version python_version
    polysquare_python_is_pypy is_pypy
    polysquare_get_find_exclusions_arguments excl_args "${exclusions}"

    # First do a pass with prospector flake* and pychecker on every single file
    # excluding the ones explicitly specified by the user as excluded
    function polysquare_run_python_linters {
        local lint_files=($(polysquare_sorted_find \
                            "." \
                            -type f \
                            -name "*.py" \
                            "${excl_args}"))

        function polysquare_run_prospector {
            local prospector_command=(prospector \
                                      --profile "${prospector_config}" \
                                      -o text \
                                      -t dodgy \
                                      -t pep257 \
                                      -t pep8 \
                                      -t pyflakes \
                                      -t pylint \
                                      -t pyroma \
                                      -F \
                                      -D \
                                      -M)

            # Don't run frosted on pypy
            if [[ "${is_pypy}" == "1" ]] ; then
                prospector_command=("${prospector_command[@]}" -t frosted)
            fi

            prospector_command=("${prospector_command[@]}" ${lint_files[*]})
            polysquare_report_failures_and_continue status \
                "${prospector_command[@]}"
        }

        function polysquare_run_flake8 {
            local flake8_command=(flake8
                                  --max-complexity=10
                                  ${lint_files[*]})
            polysquare_report_failures_and_continue status \
                "${flake8_command[@]}"
        }

        function polysquare_run_pychecker {
            local pychecker_command_base=(pychecker \
                                          --only \
                                          --limit 1000 \
                                          -Q \
                                          -8 \
                                          -2 \
                                          -1 \
                                          -a \
                                          -g \
                                          --changetypes \
                                          -v)

            which pychecker > /dev/null || return

            for file in "${lint_files[@]}" ; do
                # Ignore setup.py, it crashes pychecker
                if [[ $(basename "${file}") != "setup.py" ]] ; then
                    local pychecker_command=("${pychecker_command_base[@]}" \
                                             "${file}")
                    polysquare_report_failures_and_continue status \
                        "${pychecker_command[@]}"
                fi
            done
        }

        polysquare_run_prospector
        polysquare_run_flake8
        polysquare_run_pychecker
    }

    # This step merely runs the "vulture" tool to find unused functions. It
    # ignores test files (anything ending with _test.py)
    function polysquare_run_unused_function_check {
        local lint_files=($(polysquare_sorted_find \
                            "." \
                            -type f \
                            -name "*.py" \
                            -a -not -name "*_test.py" \
                            -a -not -name "setup.py" \
                            "${excl_args}"))
        local prospector_command=(prospector \
                                  -M \
                                  -o text \
                                  -t vulture \
                                  ${lint_files[*]})

        polysquare_fatal_error_on_failure "${prospector_command[@]}"
    }

    polysquare_task "Running linters" polysquare_run_python_linters
    polysquare_task "Running check for unused functions and identifiers" \
        polysquare_run_unused_function_check
}

polysquare_task "Checking python project" polysquare_run_python_checkers
polysquare_exit_with_failure_on_script_failures
