# /ciscripts/setup/project/configure_bii.py
#
# A script which configures and activates a bii installation
#
# See /LICENCE.md for Copyright information
"""A script which configures and activates a bii installation."""

import os
import os.path

import platform

from contextlib import contextmanager


def get(container, util, shell, ver_info):
    """Return a BiiContainer for an installed bii in container."""
    del util
    del ver_info

    version = "latest"

    # This class is intended to be used through LanguageBase, so
    # most of its methods are private
    #
    # suppress(too-few-public-methods)
    class BiiContainer(container.new_container_for("bii", version)):

        """A container representing an active bii installation."""

        # pylint can't detect that this is a new-style class
        #
        # suppress(super-on-old-class)
        def __init__(self, version, installation, shell):
            """Initialize a bii container for this version."""
            super(BiiContainer, self).__init__(installation,
                                               "bii",
                                               version,
                                               shell)
            assert os.path.exists(self._installation)

        # suppress(super-on-old-class)
        def clean(self, util_mod):
            """Clean out cruft in the container."""
            super(BiiContainer, self).clean(util_mod)
            build = container.named_cache_dir("cmake-build", ephemeral=False)
            util_mod.force_remove_tree(os.path.join(build, "bin"))
            util_mod.force_remove_tree(os.path.join(build, "lib"))

        def _active_environment(self, tuple_type):
            """Return active environment for bii container."""
            env_to_overwrite = dict()
            env_to_prepend = {
                "PATH": os.path.join(self._installation, "bin")
            }

            return tuple_type(overwrite=env_to_overwrite,
                              prepend=env_to_prepend)

    return BiiContainer(version, container.language_dir("bii"), shell)


_BII_SCRIPT = ("#!/usr/bin/env python\n"
               "import sys, os\n"
               "\n"
               "biicode_repo_path = '{}'\n"
               "\n"
               "sys.path.append(os.path.join(biicode_repo_path))\n"
               "from biicode.client.shell.bii import main\n"
               "main(sys.argv[1:])")


def _write_bii_script(util, bii_bin, bii_dir, bii_script_filename):
    """Write bii command line script."""
    os.makedirs(bii_bin)
    with open(bii_script_filename, "w") as bii_scr:
        escaped_bii_dir = bii_dir.replace("\\", "/")
        bii_scr.write(_BII_SCRIPT.format(escaped_bii_dir))
    util.make_executable(bii_script_filename)


def _setup_python_if_necessary(container, util, shell):
    """Install python 2.7 if necessary.

    This will be for platforms where python will not be installed into
    the OS container.
    """
    if platform.system() == "Linux":
        return None

    config_python = "setup/project/configure_python.py"

    py_ver = util.language_version("python2")
    py_cont = container.fetch_and_import(config_python).run(container,
                                                            util,
                                                            shell,
                                                            py_ver)
    return py_cont


@contextmanager
def _maybe_activated_python(py_cont, util):
    """Activate py_cont if it exists."""
    if py_cont:
        with py_cont.activated(util):
            yield
    else:
        yield


def _collect_nonnull_containers(util, *args, **kwargs):
    """Return all non-null args."""
    return util.make_meta_container(tuple([a for a in args if a is not None]),
                                    **kwargs)


def run(container, util, shell, ver_info, os_cont):
    """Install and activates a bii installation.

    This function returns a BiiContainer, which has a path
    and keeps a reference to its parent container.
    """
    result = util.already_completed("_POLYSQUARE_CONFIGURE_BIICODE")
    if result is not util.NOT_YET_COMPLETED:
        return result

    py_cont = _setup_python_if_necessary(container, util, shell)

    bii_dir = container.language_dir("bii")
    bii_bin = os.path.join(bii_dir, "bin")

    bii_script_filename = os.path.join(bii_bin, "bii")

    if not os.path.exists(bii_script_filename):
        util.force_remove_tree(bii_dir)
        os.makedirs(bii_dir)
        with util.in_dir(bii_dir), _maybe_activated_python(py_cont, util):
            biicode_repo = os.path.join(bii_dir, "biicode")
            with util.Task("""Downloading biicode client"""):
                remote = "git://github.com/biicode/biicode"
                util.execute(container,
                             util.long_running_suppressed_output(),
                             "git",
                             "clone",
                             remote,
                             instant_fail=True)
                with util.in_dir(biicode_repo):
                    # Remove the server-side parts
                    util.execute(container,
                                 util.output_on_fail,
                                 "git",
                                 "submodule",
                                 "deinit",
                                 "bii-server")
                    util.execute(container,
                                 util.output_on_fail,
                                 "git",
                                 "rm",
                                 "-r",
                                 "--cached",
                                 "bii-server")
                    util.execute(container,
                                 util.output_on_fail,
                                 "git",
                                 "submodule",
                                 "update",
                                 "--init",
                                 "--recursive",
                                 instant_fail=True)
                    util.force_remove_tree(os.path.join(biicode_repo,
                                                        "client",
                                                        "test"))
                    util.force_remove_tree(os.path.join(biicode_repo,
                                                        "common",
                                                        "test"))
                    _write_bii_script(util,
                                      bii_bin,
                                      bii_dir,
                                      bii_script_filename)

                    with _maybe_activated_python(py_cont, util):
                        os_cont.execute(container,
                                        util.long_running_suppressed_output(),
                                        "pip",
                                        "install",
                                        "-r",
                                        os.path.join(biicode_repo,
                                                     "common",
                                                     "requirements.txt"),
                                        instant_fail=True)
                        os_cont.execute(container,
                                        util.long_running_suppressed_output(),
                                        "pip",
                                        "install",
                                        "-r",
                                        os.path.join(biicode_repo,
                                                     "client",
                                                     "requirements.txt"),
                                        instant_fail=True)

            util.force_remove_tree(os.path.join(biicode_repo, ".git"))
            os.remove(os.path.join(biicode_repo, "client", ".git"))
            os.remove(os.path.join(biicode_repo, "common", ".git"))

    meta_container = _collect_nonnull_containers(util,
                                                 os_cont,
                                                 py_cont,
                                                 get(container,
                                                     util,
                                                     shell,
                                                     ver_info),
                                                 execute=os_cont.execute)
    util.register_result("_POLYSQUARE_CONFIGURE_BIICODE", meta_container)
    return meta_container
