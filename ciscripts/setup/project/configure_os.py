# /ciscripts/setup/project/configure_os.py
#
# A script which configures an operating system container, with a package
# manager capable of installing other binary packages.
#
# These containers can be quite heavy, so they should be avoided if
# possible.
#
# See /LICENCE.md for Copyright information
"""A script which configures an operating system container."""

import os
import os.path

import platform

import shutil

import subprocess


DEFAULT_DISTRO_FOR_SYSTEM = {
    "Linux": "Ubuntu",
    "Darwin": "OSX",
    "Windows": "Windows"
}

DEFAULT_DISTRO_RELEASE_FOR_SYSTEM = {
    "Linux": "precise",
    "Darwin": "10.10",
    "Windows": "8.1"
}


def _format_subdir_name(distro, version, arch):
    """Return subdirectory name for container information."""
    return "{d}.{v}.{a}".format(d=distro, v=version, a=arch)


def _get_python_container(cont, util, shell, py_ver_key="python3"):
    """Get python container needed to run polysquare-travis-container in."""
    config_python = "setup/project/configure_python.py"
    py_ver = util.language_version(py_ver_key)
    return cont.fetch_and_import(config_python).run(cont,
                                                    util,
                                                    shell,
                                                    py_ver)


# suppress(too-many-arguments)
def get(container,
        util,
        shell,
        ver_info,
        distro=DEFAULT_DISTRO_FOR_SYSTEM[platform.system()],
        distro_version=DEFAULT_DISTRO_RELEASE_FOR_SYSTEM[platform.system()],
        distro_arch=None):
    """Return a OSContainer for an installed operating system container."""
    del ver_info

    subdirectory_name = _format_subdir_name(distro,
                                            distro_version,
                                            distro_arch)
    py_cont = _get_python_container(container,
                                    util,
                                    shell)

    class OSContainer(container.new_container_for("os", subdirectory_name)):
        """A container representing an active operating system container."""

        # pylint can't detect that this is a new-style class
        #
        # suppress(super-on-old-class)
        def __init__(self, subdir_name, installation, shell):
            """Initialize an OSContainer installation for this subdir_name."""
            super(OSContainer, self).__init__(installation,
                                              "os",
                                              subdir_name,
                                              shell)

            self._installation = installation
            self._distro = distro
            self._distro_version = distro_version
            self._distro_arch = distro_arch
            with py_cont.activated(util):
                self._exec_script = util.which("psq-travis-container-exec")

        # suppress(super-on-old-class)
        def clean(self, util):
            """Clean out cruft in the container."""
            super(OSContainer, self).clean(util)

        def _container_specification_args(self):
            """Return arguments to specify location of container.

            These arguments should be passed to the polysquare-travis-container
            family of scripts.
            """
            args = [
                "--distro=" + self._distro,
                "--release=" + self._distro_version,
                "--local"
            ]

            if self._distro_arch:
                args.append("--arch=" + self._distro_arch)

            return args

        def execute(self, container, output_strategy, *argv, **kwargs):
            """Execute command specified by argv in this OSContainer."""
            args = ([self._exec_script,
                     self._installation,
                     "--show-output"] + self._container_specification_args() +
                    ["--"] + list(argv))
            return util.execute(container,
                                output_strategy,
                                *args,
                                **kwargs)

        # suppress(unused-function)
        def root_fs_path(self):
            """Get path to this container's package file system.

            In the case of containers on linux, this is usually the
            path which is the "fake root". On other operating system
            containers, it is effectively the prefix where programs
            are installed to.
            """
            args = self._container_specification_args()
            return subprocess.check_output(["psq-travis-container-get-root",
                                            self._installation] + args)

        def _active_environment(self, tuple_type):
            """Return variables that make up this container's active state."""
            executable_path = ""

            if platform.system() == "Linux":
                executable_path = os.pathsep.join([
                    os.path.join(self._installation,
                                 "usr",
                                 "bin"),
                    os.path.join(self._installation,
                                 "bin")
                ])
            elif platform.system() == "Darwin":
                executable_path = os.path.join(self._installation, "bin")
            elif platform.system() == "Windows":
                executable_path = os.path.join(self._installation, "bin")

            env_to_prepend = {
                "PATH": executable_path
            }

            return tuple_type(overwrite=dict(),
                              prepend=env_to_prepend)

    return OSContainer(subdirectory_name,
                       os.path.join(container.language_dir("os"),
                                    subdirectory_name),
                       shell)


def _copy_if_exists(src, dst):
    """Copy src to dst if src exists."""
    if os.path.exists(src):
        shutil.copyfile(src, dst)


# suppress(too-many-arguments)
def _update_os_container(container,
                         util,
                         py_cont,
                         os_container_path,
                         distro,
                         distro_version,
                         distro_arch,
                         distro_repositories,
                         distro_packages):
    """Re-create OS container and install packages in it."""
    repositories = (distro_repositories or
                    ".".join(["REPOSITORIES", distro, distro_version]))
    packages = (distro_packages or
                ".".join(["PACKAGES", distro, distro_version]))

    def create_command_options(updates):
        """Get options for calling the create command.

        Returns a tuple of (bool, list), where the first member is whether
        to even call the create command at all, and list is a list of
        command line options to pass.
        """
        options = list()

        repositories_exists = os.path.exists(repositories)
        packages_exists = os.path.exists(packages)

        if not (repositories_exists or packages_exists):
            return (not os.path.exists(os_container_path), [])

        if (repositories_exists and
                not util.compare_contents(repositories,
                                          "{}.REPOSITORIES".format(updates))):
            options.append("--repositories={}".format(repositories))
        if (packages_exists and
                not util.compare_contents(packages,
                                          "{}.PACKAGES".format(updates))):
            options.append("--packages={}".format(packages))

        return (True if len(options) else False, options)

    updates = os.path.join(container.named_cache_dir("container-updates",
                                                     ephemeral=False),
                           "updated-{d}-{v}-{a}".format(d=distro,
                                                        v=distro_version,
                                                        a=distro_arch))

    re_call_create, additional_options = create_command_options(updates)

    if re_call_create:
        with py_cont.activated(util):
            with util.Task("""Updating container"""):
                util.execute(container,
                             util.running_output,
                             "psq-travis-container-create",
                             os_container_path,
                             "--distro=" + distro,
                             "--release=" + distro_version,
                             "--local",
                             *additional_options,
                             instant_fail=True)

            # Store contents of REPOSITORIES and PACKAGES as they exist
            # now in the pair of updates files for this distro, release
            # and arch set. We'll compare the contents of those files
            # to these later.
            _copy_if_exists(repositories, "{}.REPOSITORIES".format(updates))
            _copy_if_exists(packages, "{}.PACKAGES".format(updates))


def _install_psq_travis_container(cont,
                                  util,
                                  shell,
                                  py_ver_key="python3"):
    """Install polysquare-travis-container and return its own container."""
    py_util = cont.fetch_and_import("python_util.py")
    py_cont = _get_python_container(cont, util, shell, py_ver_key=py_ver_key)

    with util.Task("""Installing polysquare-travis-container"""):
        with py_cont.activated(util):
            py_util.pip_install(cont,
                                util,
                                "requests",
                                "polysquare-travis-container>=0.0.33",
                                instant_fail=True)

    return py_cont


# suppress(too-many-arguments)
def run(container,
        util,
        shell,
        ver_info,
        distro=DEFAULT_DISTRO_FOR_SYSTEM[platform.system()],
        distro_version=DEFAULT_DISTRO_RELEASE_FOR_SYSTEM[platform.system()],
        distro_arch=None,
        distro_repositories=None,
        distro_packages=None):
    """Install and activates an operating system container.

    This function returns a OSContainer, which has a path
    and keeps a reference to its parent container.
    """
    subdirectory_name = _format_subdir_name(distro,
                                            distro_arch,
                                            distro_version)
    result = util.already_completed("_POLYSQUARE_CONFIGURE_OS_" +
                                    subdirectory_name)
    if result is not util.NOT_YET_COMPLETED:
        return result

    py_cont = _install_psq_travis_container(container,
                                            util,
                                            shell)

    def install(distro, distro_version, distro_arch):
        """Install distribution specified in configuration."""
        subdirectory_name = _format_subdir_name(distro,
                                                distro_version,
                                                distro_arch)
        os_container_path = os.path.join(container.language_dir("os"),
                                         subdirectory_name)

        _update_os_container(container,
                             util,
                             py_cont,
                             os_container_path,
                             distro,
                             distro_version,
                             distro_arch,
                             distro_repositories,
                             distro_packages)

        return get(container,
                   util,
                   shell,
                   ver_info,
                   distro=distro,
                   distro_version=distro_version,
                   distro_arch=distro_arch)

    with util.Task("""Configuring operating system container"""):
        os_cont = install(distro, distro_version, distro_arch)
        util.register_result("_POLYSQUARE_CONFIGURE_OS_" + subdirectory_name,
                             os_cont)
        return os_cont
