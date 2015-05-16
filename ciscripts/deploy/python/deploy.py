# /ciscripts/deploy/python/deploy.py
#
# Activate haskell container in preparation for deployment. This is required
# because we need to have pandoc available in our PATH.
#
# See /LICENCE.md for Copyright information
"""Place a symbolic link of pandoc in a writable directory in PATH."""

import os

import shutil

from collections import defaultdict


def run(cont, util, shell, argv=None):
    """Place a symbolic link of pandoc in a writable directory in PATH."""
    del argv

    def copy_pandoc_out_of_container():
        """Copy pandoc out of container.

        This ensures that when the container is removed, we still have
        access to pandoc for the deploy step, which is crucial to ensuring
        that our documentation is uploaded.
        """
        # Find the first directory in PATH that is in /home, eg
        # writable by the current user and make a symbolic link
        # from the pandoc binary to.
        if not util.which("pandoc"):
            home_dir = os.path.expanduser("~")
            languages = cont.language_dir("")
            virtualenv = os.path.join(home_dir, "virtualenv")
            # Filter out paths in the container as they won't
            # be available during the deploy step.
            for path in os.environ.get("PATH", "").split(":"):
                in_home = (os.path.commonprefix([home_dir,
                                                 path]) == home_dir)
                in_container = (os.path.commonprefix([languages,
                                                      path]) == languages)
                in_venv = (os.path.commonprefix([virtualenv,
                                                 path] == virtualenv))

                if in_home and not in_container and not in_venv:
                    destination = os.path.join(path, "pandoc")
                    with util.Task("""Creating a symbolic link from """
                                   """{0} to {1}.""".format(pandoc_binary,
                                                            destination)):
                        shutil.copy(pandoc_binary, destination)
                        break

    def install_setuptools_markdown():
        """Install setuptools-markdown in currently active python."""
        util.execute(cont,
                     util.long_running_suppressed_output(),
                     "pip",
                     "install",
                     "setuptools-markdown")

    with util.Task("""Preparing for deployment to PyPI"""):
        hs_ver = defaultdict(lambda: "7.8.4")
        hs_script = "setup/project/configure_haskell.py"
        hs_cont = cont.fetch_and_import(hs_script).get(cont,
                                                       util,
                                                       shell,
                                                       hs_ver)

        with hs_cont.activated(util):
            pandoc_binary = os.path.realpath(util.which("pandoc"))

        if os.environ.get("CI", None):
            copy_pandoc_out_of_container()
            install_setuptools_markdown()
