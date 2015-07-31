# /CMakeLists.txt
#
# Build file for main project.
#
# See /LICENCE.md for Copyright information

if (NOT CMAKE_SCRIPT_MODE_FILE)
    project (sample)
endif ()

cmake_minimum_required (VERSION 2.8 FATAL_ERROR)

set (CMAKE_MODULE_PATH 
     "${CMAKE_CURRENT_LIST_DIR}"
     "${CMAKE_MODULE_PATH}")

include (included)

if (NOT CMAKE_SCRIPT_MODE_FILE)
    include (CTest)

    enable_testing ()

    add_executable ("my_executable"
                    "${CMAKE_CURRENT_LIST_DIR}/src/main.cpp")

    add_test (NAME run_my_executable
              COMMAND "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/my_executable")
endif ()

include ("smspillaz/cmake-unit/CMakeUnit")
include ("smspillaz/cmake-unit/CMakeUnitRunner")

function (sample_test_one)

    function (_cmake_unit_configure)

        message ("Configure stage")

    endfunction ()

    cmake_unit_configure_config_only_test (CONFIGURE
                                           COMMAND _cmake_unit_configure)

endfunction ()

cmake_unit_init (NAMESPACE "sample")

if (BIICODE)

    add_bii_targets ()

endif ()