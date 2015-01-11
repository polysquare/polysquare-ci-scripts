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
        echo "A subcommand failed. "\
            "Consider deleting the travis build cache."
    fi
}

src_directory="${PWD}/tests"
build_directory="${src_directory}/build"

mkdir -p "${build_directory}" > /dev/null 2>&1
pushd "${build_directory}" > /dev/null 2>&1

cmake_cmd="cmake
${src_directory}
-Wdev
--warn-uninitialized
\\\"-G${CMAKE_GENERATOR}\\\"
"

tracefile="\"${PWD}/tests/build/coverage.trace\""
[ ! -z "${COVERAGE}" ] && cmake_cmd+=" -DCMAKE_UNIT_COVERAGE_FILE=${tracefile}"

build_cmd="cmake --build ${build_directory}"
ctest_cmd="ctest --output-on-failure"

echo "=> Testing CMake project"

echo "... Configuring project"
check_status_of "${cmake_cmd}"
echo "... Building project"
check_status_of "${build_cmd}"
echo "... Testing project"
check_status_of "${ctest_cmd}"
popd > /dev/null 2>&1

exit "${failures}"
