# /ciscripts/setup/project/configure_haskell.py
#
# A script which configures and activates a haskell installation
#
# See /LICENCE.md for Copyright information
"""A script which configures and activates a haskell installation."""

import errno

import os
import os.path

import platform

import shutil

import stat

import subprocess

import tarfile

from collections import namedtuple

from distutils.version import LooseVersion

GemDirs = namedtuple("GemDirs", "system site home")


def _no_installer_available(installation, version):
    """Placeholder for an installer function, throws an error."""
    del installation
    del version
    raise RuntimeError("""Install haskell packages in the install stage""")


def _force_makedirs(path):
    """Make directories even if path exists."""
    try:
        os.makedirs(path)
    except OSError as error:
        if error.errno != errno.EEXIST:  # suppress(PYC90)
            raise error


def _rmtree(path):
    """Remove directory at :path: if it exists."""
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.unlink(path)


def get(container, util, shell, ver_info, installer=_no_installer_available):
    """Return a HaskellContainer for an installed haskell version."""
    version = ver_info[platform.system()]
    container_path = os.path.join(container.language_dir("haskell"),
                                  "versions",
                                  version)

    class HaskellContainer(container.new_container_for("haskell", version)):

        """A container representing an active haskell installation."""

        # pylint can't detect that this is a new-style class
        #
        # suppress(super-on-old-class)
        def __init__(self, version, installation, shell, installer):
            """Initialize a haskell installation for this version."""
            super(HaskellContainer, self).__init__(installation,
                                                   "haskell",
                                                   version,
                                                   shell)

            self._version = version
            self._installation = installation
            self._internal_container = os.path.join(self._installation,
                                                    ".hsenv_" + version)
            self._installer = installer
            self._build_dir = os.path.join(container.language_dir("haskell"),
                                           "build")

        # suppress(unused-function)
        def install_cabal_pkg(self, container, pkg_name):
            """Install a cabal package.

            This function uses some tricks to avoid doing extra work. It will
            first check if the binary exists for this system type on
            https://public-hs-binaries.polysquare.org and if so, it will use
            that binary.

            If the binary doesn't exist, then it will install the
            haskell platform into this container and then use cabal to
            install the binary.
            """
            sys_id = util.get_system_identifier(container)
            url = "http://public-hs-binaries.polysquare.org/{0}/{1}"
            url = url.format(sys_id, pkg_name)
            local_file_path = os.path.join(self._internal_container,
                                           "cabal",
                                           "bin",
                                           pkg_name)

            if not os.path.exists(local_file_path):
                try:
                    _force_makedirs(os.path.dirname(local_file_path))

                    # We know this might fail, so only attempt to
                    # open the url a few times before giving up.
                    remote = util.url_opener()(url,
                                               timeout=3,
                                               retrycount=3)
                    with open(local_file_path, "wb") as local_file:
                        local_file.write(remote.read())
                        os.chmod(local_file_path,
                                 os.stat(local_file_path).st_mode |
                                 stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                except util.url_error():
                    installed_stamp = os.path.join(self._installation,
                                                   "completed")
                    if not os.path.exists(installed_stamp):
                        self._installer(self._installation,
                                        self._version,
                                        self.activate)
                        self.clean(util)
                        with open(installed_stamp, "w") as stamp:
                            stamp.write("done")

                    # Assumes that container is already active
                    util.execute(container,
                                 util.long_running_suppressed_output(),
                                 "cabal",
                                 "install",
                                 pkg_name)

        # suppress(super-on-old-class)
        def clean(self, util):
            """Clean out cruft in the container."""
            super(HaskellContainer, self).clean(util)

            # Source code
            _rmtree(os.path.join(self._internal_container, "src"))
            _rmtree(os.path.join(self._internal_container, "tmp"))
            _rmtree(os.path.join(self._internal_container, "cache"))
            _rmtree(os.path.join(self._internal_container,
                                 "cabal",
                                 "bootstrap",
                                 "lib"))

            # Documentation
            _rmtree(os.path.join(self._internal_container,
                                 "ghc",
                                 "share",
                                 "doc"))

            # Logs
            _rmtree(os.path.join(self._build_dir, "tmp"))
            _rmtree(os.path.join(self._internal_container, "hsenv.log"))

            # Object code and dynamic libraries
            debug_ghc_version = "*_debug-ghc{0}.so".format(self._version)
            l_ghc_version = "*_l-ghc{0}.so".format(self._version)
            util.apply_to_files(os.unlink,
                                self._internal_container,
                                matching=["*.o"])
            util.apply_to_files(os.unlink,
                                self._internal_container,
                                matching=[debug_ghc_version])
            util.apply_to_files(os.unlink,
                                self._internal_container,
                                matching=[l_ghc_version])
            util.apply_to_files(os.unlink,
                                self._internal_container,
                                matching=["lib*_l.a"])
            util.apply_to_files(os.unlink,
                                self._internal_container,
                                matching=["lib*_p.a"])
            util.apply_to_files(os.unlink,
                                self._internal_container,
                                matching=["lib*_thr.a"])
            util.apply_to_files(os.unlink,
                                self._internal_container,
                                matching=["lib*_debug.a"])
            util.apply_to_files(os.unlink,
                                self._internal_container,
                                matching=["*.p_"])

        def _path_prependix(self):
            """Get variables to prepend to PATH."""
            path_var_prependix_path = os.path.join(self._internal_container,
                                                   "path_var_prependix")
            if os.path.exists(path_var_prependix_path):
                with open(path_var_prependix_path, "r") as path_data:
                    path_prependix = path_data.read().strip()
            else:
                path_prependix = os.path.join(self._internal_container,
                                              "cabal",
                                              "bin")

            return path_prependix

        def _ghc_package_path(self):
            """Get GHC package path."""
            ghc_package_path_var_path = os.path.join(self._internal_container,
                                                     "ghc_package_path_var")

            if os.path.exists(ghc_package_path_var_path):
                with open(ghc_package_path_var_path, "r") as ppath_data:
                    ghc_package_path_var = ppath_data.read().strip()
            else:
                ghc_package_path_var = ""

            return ghc_package_path_var

        def _active_environment(self, tuple_type):
            """Return variables that make up this container's active state."""
            shared_lib = os.path.join(container.language_dir("haskell"),
                                      "build",
                                      "usr",
                                      "lib")

            path_prependix = self._path_prependix()
            ghc_package_path_var = self._ghc_package_path()

            pp_replacement = os.pathsep + ghc_package_path_var
            pp_replacement = pp_replacement.replace("{s}{s}"
                                                    "".format(s=os.pathsep),
                                                    os.pathsep).strip()
            while len(pp_replacement) and pp_replacement[-1] == ":":
                pp_replacement = pp_replacement[:-1]

            if LooseVersion(self._version) < LooseVersion("7.6.1"):
                db_suffix = "conf"
            else:
                db_suffix = "db"

            package_db_for_cabal = pp_replacement.replace(os.pathsep,
                                                          " --package-db=")
            package_db_for_ghc_pkg = (" --no-user-package-" +
                                      db_suffix +
                                      " " +
                                      pp_replacement.replace(os.pathsep,
                                                             " --package-" +
                                                             db_suffix +
                                                             "="))
            package_db_for_ghc = (" -no-user-package-" + db_suffix +
                                  " " + pp_replacement.replace(os.pathsep,
                                                               " -package-" +
                                                               db_suffix +
                                                               "="))
            package_db_for_ghc_mod = (" -g -no-user-package-" + db_suffix +
                                      " " +
                                      pp_replacement.replace(os.pathsep,
                                                             " -g -package-" +
                                                             db_suffix + "="))

            env_to_overwrite = {
                "PACKAGE_DB_FOR_CABAL": package_db_for_cabal,
                "PACKAGE_DB_FOR_GHC_PKG": package_db_for_ghc_pkg,
                "PACKAGE_DB_FOR_GHC": package_db_for_ghc,
                "PACKAGE_DB_FOR_GHC_MOD": package_db_for_ghc_mod,
                "HASKELL_PACAKGE_SANDBOX": ghc_package_path_var
            }

            env_to_prepend = {
                "LIBRARY_PATH": shared_lib,
                "PATH": path_prependix

            }

            return tuple_type(overwrite=env_to_overwrite,
                              prepend=env_to_prepend)

    return HaskellContainer(ver_info[platform.system()],
                            container_path,
                            shell,
                            installer)


def run(container, util, shell, ver_info):
    """Install and activates a haskell installation.

    This function returns a HaskellContainer, which has a path
    and keeps a reference to its parent container.
    """
    lang_dir = container.language_dir("haskell")
    haskell_build_dir = os.path.join(lang_dir, "build")

    def install_library_from_tar_pkg(container,
                                     remote_url,
                                     directory_name):
        """Install an autotools-distributed library at remote_url.

        The directory to change into is specified as directory.
        """
        with container.in_temp_cache_dir() as cache_dir:
            with util.in_dir(cache_dir):
                local_name = os.path.join(cache_dir,
                                          os.path.basename(remote_url))
                with open(local_name, "wb") as local_file:
                    local_file.write(util.url_opener()(remote_url).read())

                with tarfile.open(local_name) as local_tar:
                    local_tar.extractall()

                with util.in_dir(os.path.join(cache_dir,
                                              directory_name)):
                    build_dir = haskell_build_dir
                    util.execute(container,
                                 util.long_running_suppressed_output(5),
                                 "sh",
                                 os.path.join(os.getcwd(), "configure"),
                                 "--prefix={0}/usr".format(build_dir),
                                 instant_fail=True)
                    util.execute(container,
                                 util.long_running_suppressed_output(5),
                                 "make",
                                 "-j16",
                                 "install")

    def haskell_installer():
        """Install build manager."""
        def install_haskell_dependencies():
            """Install libgmp and libffi."""
            gmp_url = "https://gmplib.org/download/gmp/gmp-6.0.0a.tar.bz2"
            ffi_url = "ftp://sourceware.org/pub/libffi/libffi-3.2.1.tar.gz"

            if not os.path.exists(haskell_build_dir):
                with util.Task("""Downloading hsenv"""):
                    remote = "git://github.com/saturday06/hsenv.sh"
                    dest = haskell_build_dir
                    util.execute(container,
                                 util.output_on_fail,
                                 "git", "clone", remote, dest,
                                 instant_fail=True)

                with util.Task("""Installing libgmp"""):
                    install_library_from_tar_pkg(container,
                                                 gmp_url,
                                                 "gmp-6.0.0")

                with util.Task("""Installing libffi"""):
                    install_library_from_tar_pkg(container,
                                                 ffi_url,
                                                 "libffi-3.2.1")

        def install():
            """Install haskell version, returns a HaskellContainer."""
            def deferred_installer(installation, version, activate):
                """Closure which installs haskell on request."""
                install_haskell_dependencies()

                _force_makedirs(os.path.dirname(installation))
                with util.Task("""Installing haskell version """ + version):
                    hsenv = os.path.join(haskell_build_dir,
                                         "bin",
                                         "hsenv")

                    hsenv_args = [
                        container,
                        util.long_running_suppressed_output(),
                        "bash",
                        hsenv,
                        "--name=" + version
                    ]

                    try:
                        global_ver = subprocess.check_output(["ghc",
                                                              "--version"])
                        global_ver = global_ver.strip().split(" ")[7]
                        can_use_global_install = (global_ver == version)
                    except (subprocess.CalledProcessError, OSError):
                        can_use_global_install = False

                    if not can_use_global_install:
                        hsenv_args.append("--ghc=" + version)

                    with util.in_dir(installation):
                        util.execute(*hsenv_args,
                                     instant_fail=True)

                    with open(os.path.join(installation,
                                           ".hsenv_" + version,
                                           "cabal",
                                           "config"), "a") as cabal_config:
                        cabal_config.write("library-profiling: False\n"
                                           "executable-dynamic: False\n"
                                           "split-objs: True\n"
                                           "documentation: False\n"
                                           "tests: False\n")

                with util.Task("""Activating haskell {0}""".format(version)):
                    activate(util)

            return get(container, util, shell, ver_info, deferred_installer)

        return install

    with util.Task("""Configuring haskell"""):
        version = ver_info[platform.system()]
        haskell_container = haskell_installer()()
        with util.Task("""Activating haskell {0}""".format(version)):
            haskell_container.activate(util)

        return haskell_container
