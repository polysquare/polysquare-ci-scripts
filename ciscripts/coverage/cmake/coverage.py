# /ciscripts/coverage/cmake/coverage.py
#
# Submit coverage totals for a cmake project to coveralls
#
# See /LICENCE.md for Copyright information
"""Submit coverage totals for a cmake project to coveralls."""

import os


def run(cont, util, shell, argv=None):
    """Submit coverage total to coveralls."""
    del argv

    with util.Task("""Generating coverage report"""):
        config_os_container = "setup/project/configure_os.py"
        os_cont = cont.fetch_and_import(config_os_container).get(cont,
                                                                 util,
                                                                 shell,
                                                                 None)

        cmake_build = cont.named_cache_dir("cmake-build", False)
        tracefile = os.path.join(cmake_build, "coverage.trace")
        converter = os.path.join(cmake_build, "TracefileConverterLoc")
        if os.path.exists(converter) and os.path.exists(tracefile):
            with open(converter) as location_file:
                converter = location_file.read().strip()

            tracefile = os.path.join(cmake_build, "coverage.trace")
            lcov_output = os.path.join(os.getcwd(), "coverage.info")
            os_cont.execute(cont,
                            util.running_output,
                            "cmake",
                            "-DTRACEFILE=" + tracefile,
                            "-DLCOV_OUTPUT=" + lcov_output,
                            "-P",
                            converter)

    with util.Task("""Submitting coverage totals"""):
        if os.environ.get("CI", None) is not None:
            with util.Task("""Uploading to coveralls"""):
                util.execute(cont,
                             util.running_output,
                             "coveralls-lcov",
                             lcov_output)
