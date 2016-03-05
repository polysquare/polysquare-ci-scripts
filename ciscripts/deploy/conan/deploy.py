# /ciscripts/deploy/conan/deploy.py
#
# Copy directories into place to prepare for publishing conan project
#
# See /LICENCE.md for Copyright information
"""Place a symbolic link of pandoc in a writable directory in PATH."""

import argparse

import json

import os


def run(cont, util, shell, argv=None):
    """Place a symbolic link of pandoc in a writable directory in PATH."""
    parser = argparse.ArgumentParser("""Conan deployment""")
    parser.add_argument("--package-name",
                        help="""Package name""",
                        type=str,
                        required=True)
    result = parser.parse_args(argv)

    assert os.path.exists("conan_keys")

    with open("conan_keys", "r") as conan_keys_file:
        conan_keys = json.loads(conan_keys_file.read())

    username = conan_keys["username"]
    password = conan_keys["password"]

    cont.fetch_and_import("deploy/project/deploy.py").run(cont,
                                                          util,
                                                          shell)

    block = "{user}/{pkg}".format(user=username,
                                  pkg=result.package_name)
    upload_desc = "{pkg}/master@{block}".format(pkg=result.package_name,
                                                block=block)

    conan_cont = cont.fetch_and_import("setup/conan/setup.py").run(cont,
                                                                   util,
                                                                   shell,
                                                                   argv)

    with conan_cont.activated(util):
        with util.Task("""Logging in as {}""".format(username)):
            conan_cont.execute(cont,
                               util.running_output,
                               "conan",
                               "user",
                               username,
                               "-p",
                               password)

        with util.Task("""Deploying {} to conan""".format(upload_desc)):
            conan_cont.execute(cont,
                               util.running_output,
                               "conan",
                               "export",
                               block)
            conan_cont.execute(cont,
                               util.running_output,
                               "conan",
                               "upload",
                               upload_desc)
