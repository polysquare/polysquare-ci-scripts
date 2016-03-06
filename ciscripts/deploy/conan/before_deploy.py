# /ciscripts/deploy/conan/before_deploy.py
#
# Put conan keys in project directory before deploying.
#
# See /LICENCE.md for Copyright information
"""Put conan keys in project directory before deploying."""

import json

import os


def run(cont, util, shell, argv=None):
    """Put conan keys in project directory before deploying."""
    assert len(argv)
    argv = ["deploy/conan/deploy.py"] + (argv or [])
    cont.fetch_and_import("deploy/script/before_deploy.py").run(cont,
                                                                util,
                                                                shell,
                                                                argv)

    assert os.environ.get("CONAN_USER", None)
    assert os.environ.get("CONAN_PASS", None)
    assert os.environ.get("REPO_API_KEY", None)

    with open("conan_keys", "w") as conan_keys_file:
        conan_keys_file.write(json.dumps({
            "username": os.environ["CONAN_USER"],
            "password": os.environ["CONAN_PASS"],
            "repo_api_key": os.environ["REPO_API_KEY"]
        }))
