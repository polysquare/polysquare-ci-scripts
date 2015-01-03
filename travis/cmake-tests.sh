#!/usr/bin/env bash
# /travis/cmake-tests.sh
#
# Travis CI Script to run CMake tests.
#
# See LICENCE.md for Copyright information

failures=0

function check_status_of() {
    concat_cmd=$(echo "$@" | xargs echo)
    eval "${concat_cmd}"
    if [[ $? != 0 ]] ; then
        failures=$((failures + 1))
        printf "\nA subcommand failed. "
        printf "Consider deleting the travis build cache.\n"
    fi
}

build_directory="${PWD}/tests/build"

mkdir -p "${build_directory}" > /dev/null 2>&1
pushd "${build_directory}" > /dev/null 2>&1

cmake_cmd="cmake
${build_directory}
-Wdev
--warn-uninitialized
-G
\"${generator}\"
-DCMAKE_UNIT_LOG_COVERAGE=1
-DCMAKE_UNIT_COVERAGE_FILE=\"${PWD}/tests/build/coverage.trace\"
"

build_cmd="cmake --build ${build_directory}"
ctest_cmd="ctest --output-on-failure"

printf "\n=> Testing CMake project"

printf "\n... Configuring project"
check_status_of "${cmake_cmd}"
printf "\n... Building project"
check_status_of "${build_cmd}"
printf "\n... Testing project"
check_status_of "${ctest_cmd}"
popd > /dev/null 2>&1

exit "${failures}"
