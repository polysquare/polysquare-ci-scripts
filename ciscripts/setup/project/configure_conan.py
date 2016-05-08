# /ciscripts/setup/project/configure_conan.py
#
# A script which configures and activates a conan installation
#
# See /LICENCE.md for Copyright information
"""A script which configures and activates a conan installation."""

import os
import os.path


def get(container, util, shell, ver_info):
    """Return a ConanContainer for an installed conan in container."""
    del util
    del ver_info

    version = "latest"

    # This class is intended to be used through LanguageBase, so
    # most of its methods are private
    #
    # suppress(too-few-public-methods)
    class ConanContainer(container.new_container_for("conan", version)):
        """A container representing an active conan installation."""

        # pylint can't detect that this is a new-style class
        #
        # suppress(super-on-old-class)
        def __init__(self, version, installation, shell):
            """Initialize a conan container for this version."""
            super(ConanContainer, self).__init__(installation,
                                                 "conan",
                                                 version,
                                                 shell)
            assert os.path.exists(self._installation)

        # suppress(super-on-old-class)
        def clean(self, util_mod):
            """Clean out cruft in the container."""
            super(ConanContainer, self).clean(util_mod)
            build = container.named_cache_dir("cmake-build", ephemeral=True)
            util_mod.force_remove_tree(os.path.join(build, "bin"))
            util_mod.force_remove_tree(os.path.join(build, "lib"))

        def _active_environment(self, tuple_type):
            """Return active environment for conan container."""
            env_to_overwrite = dict()
            env_to_prepend = {
                "PATH": os.path.join(self._installation, "bin")
            }

            return tuple_type(overwrite=env_to_overwrite,
                              prepend=env_to_prepend)

    return ConanContainer(version, container.language_dir("conan"), shell)


def _setup_python(container, util, shell):
    """Get python 3 installation."""
    config_python = "setup/project/configure_python.py"

    py_ver = util.language_version("python3")
    py_cont = container.fetch_and_import(config_python).run(container,
                                                            util,
                                                            shell,
                                                            py_ver)
    return py_cont


def run(container, util, shell, ver_info, os_cont=None):
    """Install and activates a conan installation.

    This function returns a ConanContainer, which has a path
    and keeps a reference to its parent container.
    """
    result = util.already_completed("_POLYSQUARE_CONFIGURE_CONAN")
    if result is not util.NOT_YET_COMPLETED:
        return result

    py_cont = _setup_python(container, util, shell)

    with util.Task("""Installing conan"""):
        with py_cont.activated(util):
            util.execute(container,
                         util.long_running_suppressed_output(),
                         "pip",
                         "install",
                         "conan>=0.9.0")
            util.execute(container,
                         util.long_running_suppressed_output(),
                         "conan")

    executor = (os_cont.execute if os_cont else util.execute)
    meta_container = util.make_meta_container((os_cont,
                                               py_cont,
                                               get(container,
                                                   util,
                                                   shell,
                                                   ver_info)),
                                              execute=executor)
    util.register_result("_POLYSQUARE_CONFIGURE_CONAN", meta_container)
    return meta_container
