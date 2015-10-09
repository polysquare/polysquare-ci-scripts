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
    "2.8": ["{launchpad}/smspillaz/cmake-2.8.12/ubuntu {release} main"],
    "3.0": ["{launchpad}/smspillaz/cmake-3.0.2/ubuntu {release} main"],
    "latest": ["{launchpad}/smspillaz/cmake-master/ubuntu {release} main"]
}
_OSX_REPOS = defaultdict(lambda: ["homebrew/versions"])

_USER_SUFFIXES = {
    "Linux": "Ubuntu.precise",
    "Darwin": "OSX.10.10",
    "Windows": "Windows.8.1"
}


def _get_package_names(system, cmake_version, extra=None):
    """Get package names to install.

    Specify extra per-platform package names to install in extra,
    in the form of two nested dictionaries:

    packages = {
        "platform": {
            "cmake version": []
        }
    }
    """
    extra = extra or defaultdict(lambda: defaultdict(lambda: []))
    packages = defaultdict(lambda: defaultdict(lambda: []),
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

    return packages[system][cmake_version] + extra[system][cmake_version]


def _get_repositories(system, cmake_version, extra=None):
    """Get repositories to add.

    Specify extra per-platform repositories to install in extra,
    in the form of two nested dictionaries:

    packages = {
        "platform": {
            "cmake version": []
        }
    }
    """
    extra = extra or defaultdict(lambda: defaultdict(lambda: []))
    repositories = defaultdict(lambda: defaultdict(lambda: []),
                               Linux=_LINUX_REPOS,
                               Darwin=_OSX_REPOS)

    return repositories[system][cmake_version] + extra[system][cmake_version]


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
    user_file_path = os.path.join(os.getcwd(), user_file_name)
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

    # If a user file doesn't exist, then just write out our
    # own file. We don't need to worry about updating from
    # the user file.
    with open(our_file_name, "w") as destination_file:
        destination_file.truncate(0)
        destination_file.write("\n".join(updated_contents_list))

    return our_file_name


def _write_packages_file(util,
                         container_config_dir,
                         cmake_version,
                         extra_packages):
    """Write PACKAGES file in /container/_cache/container-config."""
    packages = _get_package_names(platform.system(),
                                  cmake_version,
                                  extra=extra_packages)
    return _update_from_user_file(util,
                                  "PACKAGES",
                                  packages,
                                  container_config_dir)


def _write_repos_file(util,
                      container_config_dir,
                      cmake_version,
                      extra_repos):
    """Write REPOSITORIES file in /container/_cache/container-config."""
    repos = _get_repositories(platform.system(),
                              cmake_version,
                              extra=extra_repos)
    return _update_from_user_file(util,
                                  "REPOSITORIES",
                                  repos,
                                  container_config_dir)


def _prepare_for_os_cont_setup(container_config,
                               util,
                               parse_result,
                               extra_packages,
                               extra_repos):
    """Get keyword arguments for call to /configure_os.py:run.

    This may involve writes to PACKAGES and REPOSITORIES in our container,
    so calling this function is not idempotent.
    """
    cmake_version = parse_result.cmake_version

    os_cont_kwargs = {
        "distro_packages": _write_packages_file(util,
                                                container_config,
                                                cmake_version,
                                                extra_packages),
        "distro_repositories": _write_repos_file(util,
                                                 container_config,
                                                 cmake_version,
                                                 extra_repos),
    }

    return os_cont_kwargs


def _install_cmake_linters(cont, util, shell):
    """Install cmake linters."""
    py_ver = util.language_version("python3")
    py_config_script = "setup/project/configure_python.py"
    py_util = cont.fetch_and_import("python_util.py")
    py_cont = cont.fetch_and_import(py_config_script).run(cont,
                                                          util,
                                                          shell,
                                                          py_ver)

    with util.Task("""Installing cmake linters"""):
        with py_cont.activated(util):
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


def _install_coveralls_lcov(cont, util, shell):
    """Install LCOV reporter for coveralls."""
    configure_ruby = "setup/project/configure_ruby.py"
    rb_ver = util.language_version("ruby")

    if not os.environ.get("APPVEYOR", None):
        rb_cont = cont.fetch_and_import(configure_ruby).run(cont,
                                                            util,
                                                            shell,
                                                            rb_ver)
        rb_util = cont.fetch_and_import("ruby_util.py")
        with rb_cont.activated(util):
            util.where_unavailable("coveralls-lcov",
                                   rb_util.gem_install,
                                   cont,
                                   rb_cont,
                                   util,
                                   "coveralls-lcov",
                                   instant_fail=True,
                                   path=rb_cont.executable_path())


def _parse_arguments(argv):
    """Parse arguments to run."""
    parser = argparse.ArgumentParser(description="""Set up cmake project""")
    parser.add_argument("--cmake-version",
                        help="""CMake version to install""",
                        default="latest",
                        type=str)
    return parser.parse_known_args(argv or list())


def run(cont,  # suppress(too-many-arguments)
        util,
        shell,
        argv=None,
        extra_packages=None,
        extra_repos=None):
    """Install everything necessary to test and check a cmake project.

    This script installs language runtimes to the extent that they're necessary
    for the linter checks, however those runtimes won't be active at the
    time that tests are run.
    """
    result = util.already_completed("_POLYSQUARE_SETUP_CMAKE_PROJECT")
    if result is not util.NOT_YET_COMPLETED:
        return result

    parse_result, remainder = _parse_arguments(argv)

    prj_meta = cont.fetch_and_import("setup/project/setup.py").run(cont,
                                                                   util,
                                                                   shell,
                                                                   remainder)

    with util.Task("""Setting up cmake project"""):
        _install_cmake_linters(cont, util, shell)
        _install_coveralls_lcov(cont, util, shell)

        container_config = cont.named_cache_dir("container-config")

        os_cont_setup = "setup/project/configure_os.py"
        os_cont_kw = _prepare_for_os_cont_setup(container_config,
                                                util,
                                                parse_result,
                                                extra_packages,
                                                extra_repos)

        with util.in_dir(container_config):
            os_cont = cont.fetch_and_import(os_cont_setup).run(cont,
                                                               util,
                                                               shell,
                                                               None,
                                                               **os_cont_kw)
            meta_cont = util.make_meta_container((os_cont, prj_meta),
                                                 execute=os_cont.execute)
            util.register_result("_POLYSQUARE_SETUP_CMAKE_PROJECT", meta_cont)
            return meta_cont
