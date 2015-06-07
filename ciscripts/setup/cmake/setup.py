# /ciscripts/setup/cmake/setup.py
#
# The main setup script to bootstrap and set up a cmake project.
#
# See /LICENCE.md for Copyright information
"""The main setup script to bootstrap and set up a cmake project."""

import argparse

import os

import platform

from collections import defaultdict

_LINUX_REPOS = {
    "2.8": "{launchpad}/smspillaz/cmake-2.8.12/ubuntu {release} main",
    "3.0": "{launchpad}/smspillaz/cmake-3.0/ubuntu {release} main",
    "latest": "{launchpad}/smspillaz/cmake-master/ubuntu {release} main"
}

_REPOS = defaultdict(lambda: defaultdict(lambda: ""),
                     Linux=_LINUX_REPOS)

_PACKAGES = defaultdict(lambda: defaultdict(lambda: ""),
                        Linux=["cmake", "cmake-data", "make", "gcc", "g++"],
                        Darwin=["cmake"],
                        Windows=["cmake.portable"])

_USER_PACKAGES = {
    "Linux": "PACKAGES.Ubuntu.precise",
    "Darwin": "PACKAGES.OSX.10.10",
    "Windows": "PACKAGES.Windows.8.1"
}

_USER_REPOS = {
    "Linux": "REPOSITORIES.Ubuntu.precise",
    "Darwin": "REPOSITORIES.OSX.10.10",
    "Windows": "REPOSITORIES.Windows.8.1"
}


def _read_optional_user_file(filename):
    """Read contents of filename, if it exists."""
    try:
        with open(filename) as user_file:
            return user_file.read()
    except IOError:
        return ""


def _copy_from_user_file_and_append(destination, user_file, append):
    """Copy contents of user_file and append other contents to destination."""
    user_lines = _read_optional_user_file(user_file).splitlines()
    destination_file_entries = set([l for l in user_lines if len(l)])
    destination_file_entries |= set([append])

    with open(destination, "w") as destination_file:
        destination_file.truncate(0)
        destination_file.write("\n".join(list(destination_file_entries)))


def _write_packages_file(container_config_dir):
    """Write PACKAGES file in /container/_cache/container-config."""
    packages = os.path.join(container_config_dir, "PACKAGES")
    user_packages = _USER_PACKAGES[platform.system()]
    _copy_from_user_file_and_append(packages,
                                    user_packages,
                                    " ".join(_PACKAGES[platform.system()]))
    return packages


def _write_repos_file(container_config_dir, cmake_version):
    """Write REPOSITORIES file in /container/_cache/container-config."""
    repositories = os.path.join(container_config_dir, "REPOSITORIES")
    user_repos = _USER_REPOS[platform.system()]
    cmake_repository = _REPOS[platform.system()][cmake_version]
    _copy_from_user_file_and_append(repositories,
                                    user_repos,
                                    cmake_repository)
    return repositories


def _prepare_for_os_cont_setup(container_config, util, parse_result):
    """Get keyword arguments for call to /configure_os.py:run.

    This may involve writes to PACKAGES and REPOSITORIES in our container,
    so calling this function is not idempotent.
    """
    last_updated_filename = os.path.join(container_config, "last_updated")
    last_updated = util.fetch_mtime_from(last_updated_filename)
    cmake_version = parse_result.cmake_version

    user_packages = _USER_PACKAGES[platform.system()]
    user_repos = _USER_REPOS[platform.system()]

    os_cont_kwargs = {
        "distro_packages": util.where_more_recent(user_packages,
                                                  last_updated,
                                                  _write_packages_file,
                                                  container_config),
        "distro_repositories": util.where_more_recent(user_repos,
                                                      last_updated,
                                                      _write_repos_file,
                                                      container_config,
                                                      cmake_version),
    }

    # If we set a value, then that means that we wrote a
    # REPOSITORIES or PACKAGES file for this run, so update
    # the modification time that we updated the container on.
    for value in os_cont_kwargs.values():
        if value:
            util.store_current_mtime_in(last_updated_filename)

    return os_cont_kwargs


def run(cont, util, shell, argv=None):
    """Install everything necessary to test and check a python project.

    This script installs language runtimes to the extent that they're necessary
    for the linter checks, however those runtimes won't be active at the
    time that tests are run.
    """
    parser = argparse.ArgumentParser(description="""Set up cmake project""")
    parser.add_argument("--cmake-version",
                        help="""CMake version to install""",
                        default="latest",
                        type=str)
    parse_result, remainder = parser.parse_known_args(argv or list())

    cont.fetch_and_import("setup/project/setup.py").run(cont,
                                                        util,
                                                        shell,
                                                        remainder)

    with util.Task("""Setting up cmake project"""):
        container_config = cont.named_cache_dir("container-config")

        os_cont_setup = "setup/project/configure_os.py"
        os_cont_kwargs = _prepare_for_os_cont_setup(container_config,
                                                    util,
                                                    parse_result)

        with util.in_dir(container_config):
            return cont.fetch_and_import(os_cont_setup).run(cont,
                                                            util,
                                                            shell,
                                                            None,
                                                            **os_cont_kwargs)
