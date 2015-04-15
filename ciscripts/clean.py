# /ciscripts/clean.py
#
# Call the clean() method on the main container, which will dispatch down
# to the activated sub-containers and clean them too.
#
# See /LICENCE.md for Copyright information
"""Scan for installed sub-containers and clean each one out."""


def run(container, util, shell, argv=list()):
    """Scan for installed sub-containers and clean them out."""
    del shell
    del argv

    with util.Task("Cleaning up container to prepare for cache"):
        container.clean(util)
