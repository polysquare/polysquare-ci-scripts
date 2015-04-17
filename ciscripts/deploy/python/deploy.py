# /ciscripts/deploy/python/deploy.py
#
# Activate haskell container in preparation for deployment. This is required
# because we need to have pandoc available in our PATH.
#
# See /LICENCE.md for Copyright information
"""Activate haskell container in preparation for deployment."""


def run(cont, util, shell, argv=None):
    """Activate haskell container in preparation for deployment."""
    del argv

    with util.Task("Submitting coverage totals"):
        hs_ver = "7.8.4"
        cont.fetch_and_import("setup/project/configure_haskell.py").run(cont,
                                                                        util,
                                                                        shell,
                                                                        hs_ver)
