# /ciscripts/deploy/python/deploy.py
#
# Activate haskell container in preparation for deployment. This is required
# because we need to have pandoc available in our PATH.
#
# See /LICENCE.md for Copyright information
"""Place a symbolic link of pandoc in a writable directory in PATH."""

import os


def run(cont, util, shell, argv=None):
    """Place a symbolic link of pandoc in a writable directory in PATH."""
    del argv

    with util.Task("Preparing for deployment to PyPI"):
        hs_ver = "7.8.4"
        hs_script = "setup/project/configure_haskell.py"
        hs_cont = cont.fetch_and_import(hs_script).get(cont,
                                                       util,
                                                       shell,
                                                       hs_ver)

        with hs_cont.activated(util):
            pandoc_binary = util.which("pandoc")

        if os.environ.get("CI", None):
            # Find the first directory in PATH that is in /home, eg
            # writable by the current user and make a symbolic link
            # from the pandoc binary to.
            for path in os.environ.get("PATH", "").split(":"):
                if (os.path.commonprefix(os.path.expanduser("~"),
                                         path) == os.path.expanduser("~")):
                    os.symlink(pandoc_binary, os.path.join(path, "pandoc"))
