# /CMakeLists.txt
#
# Build file for main project.
#
# See /LICENCE.md for Copyright information

if (NOT CMAKE_SCRIPT_MODE_FILE)
    project (sample)
endif ()

cmake_minimum_required (VERSION 2.8 FATAL_ERROR)

if (NOT CMAKE_SCRIPT_MODE_FILE)
    include (CTest)
    include (conanbuildinfo.cmake)

    enable_testing ()

    add_executable ("psq_test"
                    "${CMAKE_CURRENT_LIST_DIR}/src/main.cpp")
endif ()
