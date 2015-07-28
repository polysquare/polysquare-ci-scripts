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


def run(cont, util, shell, argv=None):
    """Invoke travis-bump-version if possible."""
    del shell

    parser = argparse.ArgumentParser(description="""Automatically bump """
                                                 """version on successful """
                                                 """Travis-CI builds.""")
    parser.add_argument("--bump-version-on",
                        nargs="*",
                        help="""List of files to bump versions on.""")
    result = parser.parse_known_args(argv or list())[0]

    api_key = os.environ.get("REPO_API_KEY", None)
    job_slug = os.environ.get("TRAVIS_REPO_SLUG", None)

    if api_key and job_slug:
        with util.Task("""Pushing version bump to """ + job_slug):
            util.execute(cont,
                         util.running_output,
                         "travis-bump-version",
                         *(result.bump_version_on +
                           ["--api-key",
                            api_key,
                            "--repo",
                            job_slug]),
                         allow_failure=True)
