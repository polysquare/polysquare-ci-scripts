# /ciscripts/setup/cmake/setup.py
#
# The main setup script to bootstrap and set up a cmake project.
#
# See /LICENCE.md for Copyright information
"""The main setup script to bootstrap and set up a cmake project."""

import argparse

import os

import platform

import shutil

from collections import defaultdict

_LINUX_REPOS = {
    "2.8": "{launchpad}/smspillaz/cmake-2.8.12/ubuntu {release} main",
    "3.0": "{launchpad}/smspillaz/cmake-3.0.2/ubuntu {release} main",
    "latest": "{launchpad}/smspillaz/cmake-master/ubuntu {release} main"
}
_OSX_REPOS = defaultdict(lambda: "homebrew/versions")
_REPOS = defaultdict(lambda: defaultdict(lambda: ""),
                     Linux=_LINUX_REPOS,
                     Darwin=_OSX_REPOS)

_PACKAGES = defaultdict(lambda: defaultdict(lambda: ""),
                        Linux=defaultdict(lambda: [
                            "cmake",
                            "cmake-data",
                            "make",
                            "gcc",
                            "g++"
                        ]),
                        Darwin=defaultdict(lambda: ["cmake"], **({
                            "2.8": ["cmake28"],
                            "3.0": ["cmake30"]
                        })),
                        Windows=defaultdict(lambda: ["cmake.portable"]))

_USER_SUFFIXES = {
    "Linux": "Ubuntu.precise",
    "Darwin": "OSX.10.10",
    "Windows": "Windows.8.1"
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


def _update_from_user_file(util,
                           user_file_name_template,
                           updated_contents_list,
                           container_config_dir):
    """Read :user_file_name_template: and generate file."""
    our_file_name = os.path.join(container_config_dir, user_file_name_template)
    user_file_name = "{u}.{s}".format(u=user_file_name_template,
                                      s=_USER_SUFFIXES[platform.system()])
    user_file_path = os.path.join(container_config_dir, user_file_name)
    cached_file = os.path.join(container_config_dir,
                               "{}.cache".format(user_file_name))

    if os.path.exists(user_file_path):
        if not util.compare_contents(user_file_path, cached_file):
            _copy_from_user_file_and_append(our_file_name,
                                            user_file_name,
                                            " ".join(updated_contents_list))
            shutil.copyfile(user_file_name, cached_file)
            return our_file_name

    return None


def _write_packages_file(util,
                         container_config_dir,
                         cmake_version):
    """Write PACKAGES file in /container/_cache/container-config."""
    return _update_from_user_file(util,
                                  "PACKAGES",
                                  _PACKAGES[platform.system()][cmake_version],
                                  container_config_dir)


def _write_repos_file(util,
                      container_config_dir,
                      cmake_version):
    """Write REPOSITORIES file in /container/_cache/container-config."""
    return _update_from_user_file(util,
                                  "REPOSITORIES",
                                  _REPOS[platform.system()][cmake_version],
                                  container_config_dir)


def _prepare_for_os_cont_setup(container_config,
                               util,
                               parse_result):
    """Get keyword arguments for call to /configure_os.py:run.

    This may involve writes to PACKAGES and REPOSITORIES in our container,
    so calling this function is not idempotent.
    """
    cmake_version = parse_result.cmake_version

    os_cont_kwargs = {
        "distro_packages": _write_packages_file(util,
                                                container_config,
                                                cmake_version),
        "distro_repositories": _write_repos_file(util,
                                                 container_config,
                                                 cmake_version),
    }

    return os_cont_kwargs


def run(cont, util, shell, argv=None):
    """Install everything necessary to test and check a cmake project.

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
        py_ver = defaultdict(lambda: "3.4.1")
        py_config_script = "setup/project/configure_python.py"
        py_util = cont.fetch_and_import("python_util.py")
        py_cont = cont.fetch_and_import(py_config_script).run(cont,
                                                              util,
                                                              shell,
                                                              py_ver)

        with util.Task("""Installing cmake linters"""):
            util.where_unavailable("polysquare-cmake-linter",
                                   py_util.pip_install,
                                   cont,
                                   util,
                                   "polysquare-cmake-linter",
                                   path=py_cont.executable_path())
            util.where_unavailable("cmakelint",
                                   py_util.pip_install,
                                   cont,
                                   util,
                                   "cmakelint",
                                   path=py_cont.executable_path())

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
