# /ciscripts/deploy/project/deploy.py
#
# Run travis-bump-version against specified files.
#
# This depends on the REPO_API_KEY and TRAVIS_REPO_SLUG variables to be
# set, it will silently not run without them. If calling travis-bump-version
# fails for whatever reason, then the output of the failure will be printed
# but the job will still continue.
#
# See /LICENCE.md for Copyright information
"""Run travis-bump-version against specified files."""

import argparse

import os


def _get_python_container(cont, util, shell):
    """Get python container to install linters into."""
    config_python = "setup/project/configure_python.py"
    py_ver = util.language_version("python3")

    return cont.fetch_and_import(config_python).get(cont,
                                                    util,
                                                    shell,
                                                    py_ver)


def run(cont, util, shell, argv=None):
    """Invoke travis-bump-version if possible."""
    parser = argparse.ArgumentParser(description="""Automatically bump """
                                                 """version on successful """
                                                 """Travis-CI builds.""")
    parser.add_argument("--bump-version-on",
                        nargs="*",
                        help="""List of files to bump versions on.""")
    result = parser.parse_known_args(argv or list())[0]

    api_key = os.environ.get("REPO_API_KEY", None)
    job_slug = os.environ.get("TRAVIS_REPO_SLUG", None)

    if api_key and job_slug and result.bump_version_on:
        with util.Task("""Pushing version bump to """ + job_slug):
            with _get_python_container(cont, util, shell).activated(util):
                util.execute(cont,
                             util.running_output,
                             "travis-bump-version",
                             *(result.bump_version_on +
                               ["--api-token",
                                api_key,
                                "--repo",
                                job_slug]),
                             allow_failure=True)
