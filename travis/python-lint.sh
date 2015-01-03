#!/usr/bin/env bash
# /travis/python-lint.sh
#
# Travis CI Script to lint python files
#
# See LICENCE.md for Copyright information

echo "=> Linting Python Files"
while getopts "m:" opt; do
    case "$opt" in
    m) module=$OPTARG
       ;;
    esac
done

# Create prospector configuration file
#
# The reasons for disabling the following warnings are as follows:
# - PYR06: The use of long_description is superceded by using
#          long_description_markdown_filename from setuptools-markdown
prospector_config_file="$(mktemp -d /tmp/dir.XXXXXXXX)/.prospector.yml"
cat >"${prospector_config_file}" <<EOL
ignore:
  - (^|/)\..+

pylint:
  options:
    min-public-methods: 2
    max-locals: 15
    max-returns: 6
    max-branches: 12
    max-statements: 50
    max-parents: 7
    max-attributes: 7
    max-module-lines: 1000
    max-line-length: 79

pyroma:
  disable:
    - PYR06

mccabe:
  options:
    max-complexity: 10

pep8:
  options:
    max-line-length: 79
  enable:
    - E101
    - E111
    - E112
    - E113
    - E121
    - E122
    - E123
    - E124
    - E125
    - E126
    - E127
    - E128
    - E201
    - E202
    - E203
    - E211
    - E221
    - E222
    - E223
    - E224
    - E225
    - E227
    - E228
    - E231
    - E251
    - E261
    - E262
    - E271
    - E272
    - E273
    - E274
    - E301
    - E302
    - E303
    - E304
    - E401
    - E501
    - E502
    - E701
    - E702
    - E703
    - E711
    - E712
    - E721
    - E901
    - E902
    - W191
    - W291
    - W292
    - W293
    - W391
    - W601
    - W602
    - W603
    - W604
    - N801
    - N802
    - N803
    - N804
    - N805
    - N806
    - N811
    - N812
    - N813
    - N814
EOL

failures=0

function check_status_of() {
    output_file=$(mktemp /tmp/tmp.XXXXXXX)
    concat_cmd=$(echo "$@" | xargs echo)
    eval "${concat_cmd}" > "${output_file}" 2>&1  &
    command_pid=$!
    
    # This is effectively a tool to feed the travis-ci script
    # watchdog. Print a dot every sixty seconds.
    echo "while :; sleep 60; do printf '.'; done" | bash 2> /dev/null &
    printer_pid=$!
    
    wait "${command_pid}"
    command_result=$?
    kill "${printer_pid}"
    wait "${printer_pid}" 2> /dev/null
    if [[ $command_result != 0 ]] ; then
        failures=$((failures + 1))
        cat "${output_file}"
        printf "\nA subcommand failed. "
        printf "Consider deleting the travis build cache.\n"
    fi
}

printf "   ... Installing linters "
install_linters_cmd="pip install
pylint
pylint-common
dodgy
frosted
mccabe
pep257
pep8
pyflakes
pyroma
vulture
git+https://github.com/smspillaz/prospector@prospector.fix_80
flake8
flake8-blind-except
flake8-docstrings
flake8-double-quotes
flake8-import-order
flake8-todo"

check_status_of "${install_linters_cmd}"

if [[ $TRAVIS_PYTHON_VERSION == 2.7 || $PYTHON_SETUP_LOCALLY == 1 ]] ; then
    check_status_of pip install http://sourceforge.net/projects/pychecker/files/pychecker/0.8.19/pychecker-0.8.19.tar.gz/download > /dev/null 2>&1
fi

printf "\n   ... Running linters "

# Each linter can only be run on one directory, so run it per directory
for path in setup.py "${module}" tests ; do

    # mccabe is disabled in prospector, but enabled in
    # flake8, as it can be selectively disabled per-function
    # there.
    prospector_cmd="prospector ${path}
--profile ${prospector_config_file}
-t dodgy
-t pep257
-t pep8
-t pyflakes
-t pylint
-t pyroma
-F
-D
-M
-T
-o pylint
"

    if [ "${path}" != "tests" ] ; then
        prospector_cmd+=" -t vulture"
    fi

    py_version="${TRAVIS_PYTHON_VERSION}"

    if [[ $py_version != "pypy" && $py_version != "pypy3" ]] ; then
        prospector_cmd+=" -t frosted"
    fi

    flake_cmd="flake8 ${path} --max-complexity 10"

    # flake8 and prospector check entire directories
    check_status_of "${prospector_cmd}"
    check_status_of "${flake_cmd}"
 
    # Pychecker does not work on setup.py, so skip it
    if [[ "${path}" != "setup.py" ]] ; then
        if [[ $(which pychecker) ]] ; then
            # Can't quote the glob expansion, so just use find explicitly
            # to find all python files and iterate
            find_cmd="find ${path} -type f -name \"*.py\""
            files=$(eval "${find_cmd}")
            
            for file in ${files} ; do
                pychecker_cmd="pychecker
--only
--limit 1000
-Q
-8
-2
-1
-a
-g
--changetypes
-v
${file}
"
                check_status_of "${pychecker_cmd}"
            done
        fi
    fi
done

printf "\n"

exit ${failures}
