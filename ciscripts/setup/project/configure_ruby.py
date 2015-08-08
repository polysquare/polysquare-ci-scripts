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

from collections import defaultdict, namedtuple

from contextlib import closing

GemDirs = namedtuple("GemDirs", "system site home")


def get(container, util, shell, ver_info):
    """Return a RubyContainer for an installed ruby version in container."""
    del util

    version = ver_info[platform.system()]
    container_path = os.path.join(container.language_dir("ruby"),
                                  "versions",
                                  version)
    try:
        with open(os.path.join(container_path,
                               "system-installation"), "r") as install_info:
            system_installation = install_info.read().strip()
        with open(os.path.join(container_path, "version"),
                  "r") as installed_version_info:
            version = installed_version_info.read().strip()
    except IOError:
        system_installation = container_path

    # This class is intended to be used through LanguageBase, so
    # most of its methods are private
    #
    # suppress(too-few-public-methods)
    class RubyContainer(container.new_container_for("ruby", version)):

        """A container representing an active ruby installation."""

        # pylint can't detect that this is a new-style class
        #
        # suppress(super-on-old-class)
        def __init__(self, version, installation, system_installation, shell):
            """Initialize a ruby installation for this version."""
            super(RubyContainer, self).__init__(installation,
                                                "ruby",
                                                version,
                                                shell)

            self._version = version
            self._installation = installation
            self._system_installation = system_installation
            assert os.path.exists(self._installation)
            assert os.path.exists(self._system_installation)

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

            util_mod.apply_to_files(self.delete, rb_path, matching=["*.a"])
            util_mod.apply_to_files(self.delete, rb_path, matching=["*.chm"])
            util_mod.apply_to_files(self.delete, rb_path, matching=["*.pdf"])
            util_mod.apply_to_files(self.delete, rb_path, matching=["*.html"])

            util_mod.apply_to_files(self.delete,
                                    rb_path,
                                    matching=["*unins000.exe"])
            util_mod.apply_to_files(self.delete,
                                    rb_path,
                                    matching=["*unins000.dat"])

        @staticmethod
        def _get_gem_dirs(user_installation, system_installation, version):
            """Given an installation, return a GemDirs set."""
            minor_ver = ".".join(version.split("-")[0].split(".")[:2]) + ".0"

            system_ruby_path = os.path.join(system_installation,
                                            "lib",
                                            "ruby",
                                            minor_ver)
            assert os.path.exists(system_ruby_path)

            return GemDirs(system=system_ruby_path,
                           site=os.path.join(system_installation,
                                             "lib",
                                             "ruby",
                                             "site_ruby",
                                             minor_ver),
                           home=os.path.join(user_installation))

        def gem_binary_directory(self):
            """Where binaries installed by gem install should be located."""
            return os.path.join(self._installation, "bin")

        def _active_environment(self, tuple_type):
            """Return variables that make up this container's active state."""
            gem_dirs = RubyContainer._get_gem_dirs(self._installation,
                                                   self._system_installation,
                                                   self._version)
            env_to_overwrite = {
                "GEM_PATH": "{0}{s}{1}{s}{2}".format(gem_dirs.home,
                                                     gem_dirs.site,
                                                     gem_dirs.system,
                                                     s=os.pathsep),
                "GEM_HOME": gem_dirs.home
            }
            env_to_prepend = {
                "PATH": os.pathsep.join([
                    os.path.join(self._system_installation, "bin"),
                    os.path.join(self._installation, "bin")
                ])

            }

            return tuple_type(overwrite=env_to_overwrite,
                              prepend=env_to_prepend)

    return RubyContainer(version, container_path, system_installation, shell)


def posix_ruby_installer(lang_dir, ruby_build_dir, container, util, shell):
    """Ruby installer for posix compatible operating systems."""
    if not os.path.exists(ruby_build_dir):
        with util.Task("""Downloading rvm-download"""):
            remote = "git://github.com/smspillaz/rvm-download"
            dest = ruby_build_dir
            util.execute(container,
                         util.output_on_fail,
                         "git", "clone", remote, "--branch", "fix-13", dest,
                         instant_fail=True)
            util.force_remove_tree(os.path.join(dest, ".git"))

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


def _write_system_installation_info(container,
                                    installation_dir,
                                    ruby_executable):
    """Write system installation information in lang_dir.

    This puts some information into installation_dir about the system version
    of ruby that we are using, including its actual version number
    and its install path.
    """
    assert not os.path.exists(installation_dir)
    try:
        os.makedirs(installation_dir)
    except OSError as error:
        if error.errno != errno.EEXIST:
            raise error

    ruby_path_components = os.path.split(os.path.dirname(ruby_executable))[:-1]

    with open(os.path.join(installation_dir, "system-installation"),
              "w") as install_info:
        install_info.write(os.path.join(*(ruby_path_components)))

    with open(os.path.join(installation_dir, "version"),
              "w") as installed_version_info:
        rb_util = container.fetch_and_import("ruby_util.py")
        inst_ver = rb_util.get_ruby_version_from_specified(ruby_executable,
                                                           3)
        installed_version_info.write(inst_ver)


def pre_existing_ruby(lang_dir, ruby_executable, container, util, shell):
    """Use pre-installed ruby."""
    def install(version):
        """Use system installation directory."""
        installation_dir = os.path.join(lang_dir, "versions", version)
        if not os.path.exists(installation_dir):
            _write_system_installation_info(container,
                                            installation_dir,
                                            ruby_executable)

        with util.Task("""Using system installation"""):
            return get(container, util, shell, defaultdict(lambda: version))

    return install


def _usable_preinstalled_ruby(container, version):
    """Return any pre-installed ruby matching version that we can use."""
    py_util = container.fetch_and_import("ruby_util.py")
    preinstalled_rubies = py_util.discover_rubies()
    requested_components = version.count(".") + 1

    for candidate_version, candidate_path in preinstalled_rubies.items():
        cand = ".".join(candidate_version.split(".")[:requested_components])
        if cand == version:
            return candidate_path

    return None


def run(container, util, shell, ver_info):
    """Install and activates a ruby installation.

    This function returns a RubyContainer, which has a path
    and keeps a reference to its parent container.
    """
    version = ver_info[platform.system()]
    result = util.already_completed("_POLYSQUARE_CONFIGURE_RB_" + version)
    if result is not util.NOT_YET_COMPLETED:
        return result

    lang_dir = container.language_dir("ruby")
    ruby_build_dir = os.path.join(lang_dir, "build")
    usable = _usable_preinstalled_ruby(container, version)

    with util.Task("""Configuring ruby"""):
        if usable:
            ruby_installer = pre_existing_ruby
            ruby_build_dir = usable
        elif platform.system() in ("Linux", "Darwin"):
            ruby_installer = posix_ruby_installer
        elif platform.system() == "Windows":
            ruby_installer = windows_ruby_installer

        ruby_container = ruby_installer(lang_dir,
                                        ruby_build_dir,
                                        container,
                                        util,
                                        shell)(version)

        util.register_result("_POLYSQUARE_CONFIGURE_RB_" + version,
                             ruby_container)
        return ruby_container
