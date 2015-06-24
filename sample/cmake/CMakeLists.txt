# /CMakeLists.txt
#
# Build file for main project.
#
# See /LICENCE.md for Copyright information

project (sample)

cmake_minimum_required (VERSION 2.8 FATAL_ERROR)

include ("included.cmake")

include (CTest)

enable_testing ()

add_executable (my_executable
                "${CMAKE_CURRENT_SOURCE_DIR}/src/main.cpp")

add_test (NAME run_my_executable
          COMMAND "${CMAKE_CURRENT_BINARY_DIR}/my_executable")
