# /ciscripts/check/psqcppconan/check.py
#
# Run tests and static analysis checks on a polysquare conan c++ project.
#
# See /LICENCE.md for Copyright information
"""Run tests and static analysis checks on a polysquare conan c++ project."""

import argparse

import os


def run(cont, util, shell, argv=None):
    """Run checks on this conan project."""
    parser = argparse.ArgumentParser(description="""Run conan checks""")
    parser.add_argument("--run-test-binaries",
                        nargs="*",
                        type=str,
                        help="""Files relative to the build dir to run""")
    result, remainder = parser.parse_known_args(argv or list())

    conan_check_script = "check/conan/check.py"
    conan_check = cont.fetch_and_import(conan_check_script)

    def _during_test(cont, executor, util, build):
        """Run the specified test binaries with the --tap switch.

        We then pipe the output into tap-mocha-reporter.
        """
        del build

        for binary in result.run_test_binaries or list():
            if not os.path.exists(binary) and os.path.exists(binary + ".exe"):
                binary = binary + ".exe"

            executor(cont,
                     util.running_output,
                     os.path.join(os.getcwd(), binary))
            util.print_message(binary)

    kwargs = {
        "kind": "polysquare conan c++",
        "during_test": _during_test
    }

    return conan_check.run(cont,
                           util,
                           shell,
                           argv=remainder,
                           override_kwargs=kwargs)
