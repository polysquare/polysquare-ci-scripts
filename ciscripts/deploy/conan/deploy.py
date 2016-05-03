# /ciscripts/deploy/conan/deploy.py
#
# Copy directories into place to prepare for publishing conan project
#
# See /LICENCE.md for Copyright information
"""Place a symbolic link of pandoc in a writable directory in PATH."""

import argparse

import json

import os

import platform

from contextlib import contextmanager

try:
    from io import StringIO
except ImportError:
    from cStringIO import StringIO   # suppress(import-error)


def _get_python_container(cont, util, shell):
    """Get a python 2.7.9 installation if necessary."""
    if platform.system() == "Linux":
        return None

    py_ver = util.language_version("python2")
    config_python = "setup/project/configure_python.py"
    return cont.fetch_and_import(config_python).get(cont,
                                                    util,
                                                    shell,
                                                    py_ver)


@contextmanager
def _maybe_activate_python(py_cont, util):
    """Activate py_cont if it exists."""
    if py_cont:
        with py_cont.activated(util):
            yield
    else:
        yield


def updated_dict(input_dict, update):
    """Apply update to input_dict and return the result."""
    copy = input_dict.copy()
    copy.update(update)
    return copy


@contextmanager
def temporary_environment(environment):
    """Run child code inside temporarily set environment variables."""
    try:
        backup = os.environ.copy()
        os.environ = environment
        yield os.environ
    finally:
        os.environ = backup


@contextmanager
def captured_messages(util):
    """Capture printed messages."""
    old_buffer = util.PRINT_MESSAGES_TO
    try:
        util.PRINT_MESSAGES_TO = StringIO()
        yield util.PRINT_MESSAGES_TO
    finally:
        util.PRINT_MESSAGES_TO = old_buffer


# suppress(too-many-arguments)
def run_deploy(cont, util, conan_cont, pkg_name, version, block):
    """Run the deploy step and set CONAN_VERSION_OVERRIDE to version."""
    update = {"CONAN_VERSION_OVERRIDE": version} if version else {}
    upload_desc = "{pkg}/{version}@{block}".format(pkg=pkg_name,
                                                   version=version,
                                                   block=block)
    with util.Task("""Deploying {} to conan""".format(upload_desc)):
        with temporary_environment(updated_dict(os.environ, update)):
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

    os.environ["REPO_API_KEY"] = str(conan_keys["repo_api_key"])
    cont.fetch_and_import("deploy/project/deploy.py").run(cont,
                                                          util,
                                                          shell)

    block = "{user}/{pkg}".format(user=username,
                                  pkg=result.package_name)

    cont.fetch_and_import("deploy/project/deploy.py").run(cont,
                                                          util,
                                                          shell,
                                                          ["--bump-version-on",
                                                           "conanfile.py"])

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

        run_deploy(cont,
                   util,
                   conan_cont,
                   result.package_name,
                   "master",
                   block)

        with _maybe_activate_python(_get_python_container(cont,
                                                          util,
                                                          shell),
                                    util):
            with captured_messages(util) as version_stream:
                conan_cont.execute(cont,
                                   util.running_output,
                                   "python",
                                   "-c",
                                   "import conanfile; "
                                   "print(conanfile.VERSION)")

        version_stream.seek(0)
        version = str(version_stream.read()).strip()
        run_deploy(cont,
                   util,
                   conan_cont,
                   result.package_name,
                   version,
                   block)
