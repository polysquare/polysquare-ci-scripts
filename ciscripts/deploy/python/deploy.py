# /ciscripts/deploy/python/deploy.py
#
# Activate haskell container in preparation for deployment. This is required
# because we need to have pandoc available in our PATH.
#
# See /LICENCE.md for Copyright information
"""Place a symbolic link of pandoc in a writable directory in PATH."""

import os

import shutil


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
            path = util.find_usable_path_in_homedir(cont)
            destination = os.path.join(path, "pandoc")
            with util.Task("""Copying pandoc binary from """
                           """{0} to {1}.""".format(pandoc_binary,
                                                    destination)):
                shutil.copy(pandoc_binary, destination)

    def install_setuptools_markdown():
        """Install setuptools-markdown in currently active python."""
        util.execute(cont,
                     util.long_running_suppressed_output(),
                     "pip",
                     "install",
                     "setuptools-markdown")

    cont.fetch_and_import("deploy/project/deploy.py").run(cont,
                                                          util,
                                                          shell,
                                                          ["--bump-version-on",
                                                           "setup.py"])

    with util.Task("""Preparing for deployment to PyPI"""):
        hs_ver = util.language_version("haskell")
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
