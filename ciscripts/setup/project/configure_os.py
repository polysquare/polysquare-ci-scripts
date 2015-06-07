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

import tempfile

from collections import defaultdict


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
    container_path = os.path.join(container.language_dir("os"),
                                  subdirectory_name)

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

        # suppress(super-on-old-class)
        def clean(self, util):
            """Clean out cruft in the container."""
            super(OSContainer, self).clean(util)

        def execute(self, container, output_strategy, *argv, **kwargs):
            """Execute command specified by argv in this OSContainer."""
            use_args = []

            if self._distro_arch:
                use_args.append("--arch=" + self._distro_arch)

            use_args.append("--")
            use_args.extend(list(argv))

            return util.execute(container,
                                output_strategy,
                                "psq-travis-container-exec",
                                self._installation,
                                "--show-output",
                                "--distro=" + self._distro,
                                "--release=" + self._distro_version,
                                *use_args,
                                **kwargs)

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
                       container_path,
                       shell)


# suppress(too-many-arguments)
def _update_os_container(container,
                         util,
                         os_container_path,
                         distro,
                         distro_version,
                         distro_arch,
                         distro_repositories,
                         distro_packages):
    """Re-create OS container and install packages in it."""
    def create_command_options(updates_filename):
        """Get options for calling the create command.

        Returns a tuple of (bool, list), where the first member is whether
        to even call the create command at all, and list is a list of
        command line options to pass.
        """
        def exists_and_is_more_recent(filename, mtime):
            """Return true if this filename exists and is more recent."""
            if not os.path.exists(filename):
                return False

            if os.stat(filename).st_mtime > mtime:
                return True

        repositories = (distro_repositories or
                        ".".join(["REPOSITORIES", distro, distro_version]))
        packages = (distro_packages or
                    ".".join(["PACKAGES", distro, distro_version]))

        additional_options = list()

        # The time the distro container was last updated
        try:
            with open(updates_filename) as updates_file:
                last_updated = float(updates_file.read())
                re_call_create = False
        except (IOError, ValueError):
            last_updated = float(0)
            re_call_create = True

        if exists_and_is_more_recent(repositories, last_updated):
            additional_options.append("--repositories=" + repositories)
            re_call_create = True

        if exists_and_is_more_recent(packages, last_updated):
            additional_options.append("--packages=" + packages)
            re_call_create = True

        return (re_call_create, additional_options)

    container_updates_dir = container.named_cache_dir("container-updates",
                                                      ephemeral=False)
    updates = os.path.join(container_updates_dir,
                           "updated-{d}-{v}-{a}".format(d=distro,
                                                        v=distro_version,
                                                        a=distro_arch))

    with util.Task("""Updating container"""):
        re_call_create, additional_options = create_command_options(updates)

        if re_call_create:
            util.execute(container,
                         util.running_output,
                         "psq-travis-container-create",
                         os_container_path,
                         "--distro=" + distro,
                         "--release=" + distro_version,
                         *additional_options,
                         instant_fail=True)

            # Get the mtime of a temporary file to set as our baseline
            # in the future
            with open(updates, "w") as updates_file:
                with tempfile.NamedTemporaryFile() as temp:
                    temp.write("contents".encode())
                    updates_file.truncate(0)
                    updates_file.write(str(os.stat(temp.name).st_mtime))


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
    config_python = "setup/project/configure_python.py"

    py_ver = defaultdict(lambda: "2.7.9")
    py_util = container.fetch_and_import("python_util.py")
    py_cont = container.fetch_and_import(config_python).run(container,
                                                            util,
                                                            shell,
                                                            py_ver)

    with util.Task("""Installing polysquare-travis-container"""):
        remote = ("https://github.com/polysquare/"
                  "polysquare-travis-container/tarball/master")
        util.where_unavailable("psq-travis-container-create",
                               py_util.pip_install,
                               py_cont,
                               util,
                               remote,
                               "--process-dependency-links",
                               path=py_cont.executable_path(),
                               instant_fail=True)

    def install(distro, distro_version, distro_arch):
        """Install distribution specified in configuration."""
        subdirectory_name = _format_subdir_name(distro,
                                                distro_version,
                                                distro_arch)
        os_container_path = os.path.join(container.language_dir("os"),
                                         subdirectory_name)

        _update_os_container(container,
                             util,
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
        return install(distro, distro_version, distro_arch)
