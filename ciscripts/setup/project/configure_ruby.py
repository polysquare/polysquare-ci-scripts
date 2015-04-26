# /ciscripts/setup/project/configure_ruby.py
#
# A script which configures and activates a ruby installation
#
# See /LICENCE.md for Copyright information
"""A script which configures and activates a ruby installation."""

import os
import os.path

import platform

from collections import namedtuple

GemDirs = namedtuple("GemDirs", "system site home")


def get(container, util, shell, version):
    """Return a RubyContainer for an installed ruby version in container."""
    del util

    container_path = os.path.join(container.language_dir("ruby"),
                                  "versions",
                                  version)

    # This class is intended to be used through LanguageBase, so
    # most of its methods are private
    #
    # suppress(too-few-public-methods)
    class RubyContainer(container.new_container_for("ruby", version)):

        """A container representing an active ruby installation."""

        # pylint can't detect that this is a new-style class
        #
        # suppress(super-on-old-class)
        def __init__(self, version, installation, shell):
            """Initialize a ruby installation for this version."""
            super(RubyContainer, self).__init__(installation,
                                                "ruby",
                                                version,
                                                shell)

            self._version = version
            self._installation = installation
            assert os.path.exists(self._installation)

            if (platform.system() == "Darwin" and
                    not os.path.exists("/etc/openssl/cert.pem")):
                raise Exception("""/System/Library/OpenSSL/cert.pem needs """
                                """to be symlinked to /etc/openssl/cert.pem """
                                """in order to work around broken rvm """
                                """builds.""")

        def clean(self, _):
            """Clean out container."""
            pass

        @staticmethod
        def _get_gem_dirs(installation, version):
            """Given an installation, return a GemDirs set."""
            minor_ver = ".".join(version.split("-")[0].split(".")[:2]) + ".0"

            system_ruby_path = os.path.join(installation,
                                            "lib",
                                            "ruby",
                                            minor_ver)
            assert os.path.exists(system_ruby_path)

            return GemDirs(system=system_ruby_path,
                           site=os.path.join(installation,
                                             "lib",
                                             "ruby",
                                             "site_ruby",
                                             minor_ver),
                           home=os.path.join(installation))

        def _active_environment(self, tuple_type):
            """Return variables that make up this container's active state."""
            gem_dirs = RubyContainer._get_gem_dirs(self._installation,
                                                   self._version)
            env_to_overwrite = {
                "GEM_PATH": "{0}:{1}:{2}".format(gem_dirs.home,
                                                 gem_dirs.site,
                                                 gem_dirs.system),
                "GEM_HOME": gem_dirs.home
            }
            env_to_prepend = {
                "PATH": os.path.join(self._installation, "bin")
            }

            return tuple_type(overwrite=env_to_overwrite,
                              prepend=env_to_prepend)

    return RubyContainer(version, container_path, shell)


def run(container, util, shell, version):
    """Install and activates a ruby installation.

    This function returns a RubyContainer, which has a path
    and keeps a reference to its parent container.
    """
    lang_dir = container.language_dir("ruby")
    ruby_build_dir = os.path.join(lang_dir, "build")

    def ruby_installer():
        """Get ruby installer (rvm-download)."""
        if not os.path.exists(ruby_build_dir):
            with util.Task("""Downloading rvm-download"""):
                remote = "git://github.com/garnieretienne/rvm-download"
                dest = ruby_build_dir
                util.execute(container,
                             util.output_on_fail,
                             "git", "clone", remote, dest,
                             instant_fail=True)

        def install(version):
            """Install ruby version, returns a RubyContainer."""
            ruby_container_dir = container.language_dir("ruby")
            ruby_version_container = os.path.join(ruby_container_dir,
                                                  "versions",
                                                  version)

            if not os.path.exists(ruby_version_container):
                os.makedirs(ruby_version_container)
                with util.Task("""Installing ruby version """ + version):
                    rvm_download = os.path.join(ruby_build_dir,
                                                "bin",
                                                "rbenv-download")
                    util.execute(container,
                                 util.long_running_suppressed_output(),
                                 "bash", rvm_download, version,
                                 env={
                                     "RBENV_ROOT": ruby_container_dir
                                 },
                                 instant_fail=True)

            return get(container, util, shell, version)

        return install

    with util.Task("""Configuring ruby"""):
        ruby_container = ruby_installer()(version)
        with util.Task("""Activating ruby """ + version):
            ruby_container.activate(util)

        return ruby_container
