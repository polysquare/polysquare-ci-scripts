# /ciscripts/coverage/cmake/coverage.py
#
# Submit coverage totals for a cmake project to coveralls
#
# See /LICENCE.md for Copyright information
"""Submit coverage totals for a cmake project to coveralls."""

import os

from collections import defaultdict

from contextlib import contextmanager


@contextmanager
def _activated_ruby_container(cont, util):
    """Activate ruby container so we can run LCOV report generator."""
    ruby_version = defaultdict(lambda: "1.9.3",
                               Linux="1.9.3",
                               Windows="2.1.6",
                               Darwin="2.0.0")

    configure_ruby = "setup/project/configure_ruby.py"
    rb_cont = cont.fetch_and_import(configure_ruby).run(cont,
                                                        util,
                                                        None,
                                                        ruby_version)

    with rb_cont.activated(util):
        yield


def _submit_totals(cont, util):
    """Submit coverage totals."""
    lcov_output = os.path.join(os.getcwd(), "coverage.info")
    if os.path.exists(lcov_output):
        with util.Task("""Submitting coverage totals to coveralls"""):
            with _activated_ruby_container(cont, util):
                util.execute(cont,
                             util.running_output,
                             "coveralls-lcov",
                             lcov_output)
    else:
        with util.Task("""Not submitting coverage totals as """
                       """/coverage.info does not exist"""):
            pass


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

    if os.environ.get("CI", None) is not None:
        _submit_totals(cont, util)
