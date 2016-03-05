# /ciscripts/deploy/conan/deploy.py
#
# Copy directories into place to prepare for publishing conan project
#
# See /LICENCE.md for Copyright information
"""Place a symbolic link of pandoc in a writable directory in PATH."""

import argparse

import os


def run(cont, util, shell, argv=None):
    """Place a symbolic link of pandoc in a writable directory in PATH."""
    parser = argparse.ArgumentParser("""Conan deployment""")
    parser.add_argument("--package-name",
                        help="""Package name""",
                        type=str,
                        required=True)
    result = parser.parse_args(argv)

    cont.fetch_and_import("deploy/project/deploy.py").run(cont,
                                                          util,
                                                          shell)

    assert os.environ.get("CONAN_USER", None) is not None
    assert os.environ.get("CONAN_PASS", None) is not None

    user = os.environ["CONAN_USER"]
    password = os.environ["CONAN_PASS"]

    block = "{user}/{pkg}".format(user=user, pkg=result.package_name)
    upload_desc = "{pkg}/master@{block}".format(pkg=result.package_name,
                                                block=block)

    conan_cont = cont.fetch_and_import("setup/conan/setup.py").run(cont,
                                                                   util,
                                                                   shell,
                                                                   argv)

    with conan_cont.activated(util):
        with util.Task("""Logging in as {}""".format(user)):
            util.execute(cont,
                         util.running_output,
                         "conan",
                         "user",
                         user,
                         "-p",
                         password)

        with util.Task("""Deploying {} to conan""".format(upload_desc)):
            util.execute(cont,
                         util.running_output,
                         "conan",
                         "export",
                         block)
            util.execute(cont,
                         util.running_output,
                         "conan",
                         "upload",
                         upload_desc)