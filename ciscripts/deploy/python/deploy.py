# /ciscripts/deploy/python/deploy.py
#
# Install setuptools-markdown
#
# See /LICENCE.md for Copyright information
"""Install setuptools-markdown."""


def run(cont, util, shell, argv=None):
    """Install setuptools-markdown."""
    del argv

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
        install_setuptools_markdown()
