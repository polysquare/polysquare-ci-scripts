# /ciscripts/setup/psqcppconan/setup.py
#
# The main setup script to bootstrap and set up a psqcppconan project.
#
# See /LICENCE.md for Copyright information
"""The main setup script to bootstrap and set up a psqcppconan project."""


def run(cont, util, shell, argv=None):
    """Install everything necessary for a polysquare C++ project."""
    result = util.already_completed("_POLYSQUARE_SETUP_PSQCPPCONAN_PROJECT")
    if result is not util.NOT_YET_COMPLETED:
        return result

    with util.Task("""Setting up polysquare C++ project"""):
        conan_meta = cont.fetch_and_import("setup/conan/setup.py").run(cont,
                                                                       util,
                                                                       shell,
                                                                       argv)

    util.register_result("_POLYSQUARE_SETUP_PSQCPPCONAN_PROJECT", conan_meta)
    return conan_meta
