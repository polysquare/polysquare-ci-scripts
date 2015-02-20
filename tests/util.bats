#!/usr/bin/env bats
# /tests/util.bats
#
# Tests for the utility functions in travis/
#
# See LICENCE.md for Copyright information

load polysquare_ci_scripts_helper
source "${POLYSQUARE_TRAVIS_SCRIPTS}/util.sh"

@test "Calling print task expands arguments" {
    run polysquare_print_task arg1 arg2 arg3
    [ "${lines[0]}" = "=> arg1 arg2 arg3" ]
}

@test "Calling print task uses single string" {
    run polysquare_print_task "arg1 arg2 arg3"
    [ "${lines[0]}" = "=> arg1 arg2 arg3" ]
}

@test "Calling print status prints dots then args" {
    run polysquare_print_status "arg1 arg2 arg3"
    [ "${lines[0]}" = "   ... arg1 arg2 arg3" ]
}

@test "Calling print error prints bangs then args" {
    run polysquare_print_error "arg1 arg2 arg3"
    [ "${lines[0]}" = "   !!! arg1 arg2 arg3" ]
}

@test "Repeat switch for list" {
    polysquare_repeat_switch_for_list rval "-x" one two three
    [ "${rval}" = "-x one two three" ]
}

@test "Single find extension argument" {
    polysquare_get_find_extensions_arguments rval sh
    [ "${rval}" = " -name \"*.sh\"" ]
}

@test "Monitoring command status with true return value" {
    run print_returned_args_on_newlines \
        polysquare_monitor_command_status \
        1 \
        rval \
        true
    [ "${lines[0]}" = "0" ]
}

@test "Monitoring command status with false return value" {
    run print_returned_args_on_newlines \
        polysquare_monitor_command_status \
        1 \
        rval \
        false

    [ "${lines[0]}" = "1" ]
}

@test "Monitoring command output to standard output" {
    run print_returned_args_on_newlines \
        polysquare_monitor_command_output \
        2 \
        command_status \
        command_output \
        echo stdout

    command_output=$(cat "${lines[1]}")

    [ "${command_output}" = "stdout" ]
}

@test "Command with status printed when reporting failures and continuing" {
    run polysquare_report_failures_and_continue \
        command_status \
        false

    [ "${lines[0]}" = "   !!! Subcommand false failed with 1" ]
}

@test "Successful status returned when reporting failures and continuing" {
    run print_returned_args_on_newlines \
        polysquare_report_failures_and_continue \
        1 \
        command_status \
        true

    command_status="${lines[0]}"

    [ "${command_status}" = "0" ]
}

@test "Fail status returned when reporting failures and continuing" {
    run print_returned_args_on_newlines \
        polysquare_report_failures_and_continue \
        1 \
        command_status \
        false

    command_status="${lines[0]}"

    [ "${command_status}" = "1" ]
}

@test "Successful status returned when noting failures and continuing" {
    run print_returned_args_on_newlines \
        polysquare_note_failure_and_continue \
        1 \
        command_status \
        true

    command_status="${lines[0]}"

    [ "${command_status}" = "0" ]
}

@test "Fail status returned when noting failures and continuing" {
    run print_returned_args_on_newlines \
        polysquare_note_failure_and_continue \
        1 \
        command_status \
        false

    command_status="${lines[0]}"

    [ "${command_status}" = "1" ]
}

@test "Exit with fatal error when reporting a failure" {
    run polysquare_fatal_error_on_failure \
        false

    [ "${status}" = "1" ]
}

@test "Exit with success when no fatal errors to be reported" {
    polysquare_fatal_error_on_failure true
    polysquare_fatal_error_on_failure true
}

@test "Show failing subcommand and status when exiting on fatal error" {
    run polysquare_fatal_error_on_failure \
        false

    [ "${lines[0]}" = "   !!! Subcommand false failed with 1" ]
}


