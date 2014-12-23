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

echo "   ... Installing linters"
pip install \
    pylint \
    pylint-common \
    dodgy \
    frosted \
    mccabe \
    pep257 \
    pep8 \
    pyflakes \
    pyroma \
    vulture \
    prospector \
    flake8 \
    flake8-blind-except \
    flake8-docstrings \
    flake8-double-quotes \
    flake8-import-order \
    flake8-todo > /dev/null 2>&1

if [[ $TRAVIS_PYTHON_VERSION == 2.7 || $PYTHON_SETUP_LOCALLY == 1 ]] ; then
    pip install http://sourceforge.net/projects/pychecker/files/pychecker/0.8.19/pychecker-0.8.19.tar.gz/download > /dev/null 2>&1
fi

echo "   ... Running linters"

# Create prospector configuration file
prospector_config_file="$(mktemp -d)/.prospector.yml"
cat >"${prospector_config_file}" <<EOL
ignore:
  - (^|/)\..+

pylint:
  disable:
    - R0904
    - R0903

  options:
    max-locals: 15
    max-returns: 6
    max-branches: 12
    max-statements: 50
    max-parents: 7
    max-attributes: 7
    max-module-lines: 1000
    max-line-length: 79

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
    output_file=$(mktemp)
    concat_cmd=$(echo "$@" | xargs echo)
    eval "${concat_cmd}" > "${output_file}" 2>&1
    if [[ $? != 0 ]] ; then
        failures=$((failures + 1))
        cat "${output_file}"
    fi
}

# Each linter can only be run on one directory, so run it per directory
for path in setup.py "${module}" tests ; do

    prospector_cmd="prospector ${path}
--profile ${prospector_config_file}
-w dodgy
-w frosted
-w mccabe
-w pep257
-w pep8
-w pyflakes
-w pylint
-w pyroma
-F
-D
-M
-T
-o pylint
"

    if [[ "${path}" != "tests" ]] ; then
        prospector_cmd+="-w vulture"
    fi

    flake_cmd="flake8 ${path}"

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

exit ${failures}
