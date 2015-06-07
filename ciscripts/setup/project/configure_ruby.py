# /ciscripts/setup/project/configure_ruby.py
#
# A script which configures and activates a ruby installation
#
# See /LICENCE.md for Copyright information
"""A script which configures and activates a ruby installation."""

import errno

import os
import os.path

import platform

import shutil

from collections import defaultdict, namedtuple

from contextlib import closing

GemDirs = namedtuple("GemDirs", "system site home")


def get(container, util, shell, ver_info):
    """Return a RubyContainer for an installed ruby version in container."""
    del util

    version = ver_info[platform.system()]

    if os.environ.get("POLYSQUARE_PREINSTALLED_RUBY", None):
        container_path = os.environ["POLYSQUARE_PREINSTALLED_RUBY"]
    else:
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

        # suppress(super-on-old-class)
        def clean(self, util_mod):
            """Clean out container."""
            super(RubyContainer, self).clean(util_mod)

            rb_path = self._installation

            util_mod.apply_to_files(os.unlink, rb_path, matching=["*.a"])
            util_mod.apply_to_files(os.unlink, rb_path, matching=["*.chm"])
            util_mod.apply_to_files(os.unlink, rb_path, matching=["*.pdf"])
            util_mod.apply_to_files(os.unlink, rb_path, matching=["*.html"])

            util_mod.apply_to_files(os.unlink,
                                    rb_path,
                                    matching=["*unins000.exe"])
            util_mod.apply_to_files(os.unlink,
                                    rb_path,
                                    matching=["*unins000.dat"])

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
                "GEM_PATH": "{0}{s}{1}{s}{2}".format(gem_dirs.home,
                                                     gem_dirs.site,
                                                     gem_dirs.system,
                                                     s=os.pathsep),
                "GEM_HOME": gem_dirs.home
            }
            env_to_prepend = {
                "PATH": os.path.join(self._installation, "bin")
            }

            return tuple_type(overwrite=env_to_overwrite,
                              prepend=env_to_prepend)

    return RubyContainer(version, container_path, shell)


def posix_ruby_installer(lang_dir, ruby_build_dir, container, util, shell):
    """Ruby installer for posix compatible operating systems."""
    if not os.path.exists(ruby_build_dir):
        with util.Task("""Downloading rvm-download"""):
            remote = "git://github.com/garnieretienne/rvm-download"
            dest = ruby_build_dir
            util.execute(container,
                         util.output_on_fail,
                         "git", "clone", remote, dest,
                         instant_fail=True)
            shutil.rmtree(os.path.join(dest, ".git"))

    def install(version):
        """Install ruby version, returns a RubyContainer."""
        ruby_version_container = os.path.join(lang_dir,
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
                                 "RBENV_ROOT": lang_dir,
                                 "RUBIES_ROOT": os.path.join(lang_dir,
                                                             "versions")
                             },
                             instant_fail=True)

        return get(container, util, shell, defaultdict(lambda: version))

    return install


def windows_ruby_installer(lang_dir, ruby_build_dir, container, util, shell):
    """Ruby installer for Windows."""
    try:
        os.makedirs(ruby_build_dir)
    except OSError as error:
        if error.errno != errno.EEXIST:   # suppress(PYC90)
            raise error

    def install(version):
        ruby_version_container = os.path.join(lang_dir, "versions", version)
        if not os.path.exists(ruby_version_container):
            url = ("http://dl.bintray.com/oneclick/rubyinstaller/"
                   "rubyinstaller-{ver}.exe").format(ver=version)
            with open(os.path.join(ruby_build_dir,
                                   version + "-install.exe"),
                      "wb") as installer:
                with closing(util.url_opener()(url)) as remote:
                    installer.write(remote.read())

            with util.Task("""Installing ruby version """ + version):
                installer = os.path.realpath(installer.name)
                util.execute(container,
                             util.long_running_suppressed_output(),
                             installer,
                             "/verysilent",
                             "/dir={0}".format(ruby_version_container))
                os.unlink(installer)

        return get(container, util, shell, defaultdict(lambda: version))

    return install


def pre_existing_ruby(lang_dir, ruby_build_dir, container, util, shell):
    """Use pre-installed ruby."""
    del ruby_build_dir
    del lang_dir

    def install(version):
        """Use system installation directory."""
        with util.Task("Using system installation"):
            return get(container, util, shell, defaultdict(lambda: version))

    return install


def run(container, util, shell, ver_info):
    """Install and activates a ruby installation.

    This function returns a RubyContainer, which has a path
    and keeps a reference to its parent container.
    """
    lang_dir = container.language_dir("ruby")
    ruby_build_dir = os.path.join(lang_dir, "build")

    with util.Task("""Configuring ruby"""):
        if (os.environ.get("POLYSQUARE_PREINSTALLED_RUBY", None) and
                os.path.exists(os.environ["POLYSQUARE_PREINSTALLED_RUBY"])):
            ruby_installer = pre_existing_ruby
        elif platform.system() in ("Linux", "Darwin"):
            ruby_installer = posix_ruby_installer
        elif platform.system() == "Windows":
            ruby_installer = windows_ruby_installer

        version = ver_info[platform.system()]
        ruby_container = ruby_installer(lang_dir,
                                        ruby_build_dir,
                                        container,
                                        util,
                                        shell)(version)
        with util.Task("""Activating ruby """ + version):
            ruby_container.activate(util)

        return ruby_container
