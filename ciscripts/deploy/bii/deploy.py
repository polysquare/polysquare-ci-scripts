# /ciscripts/deploy/bii/deploy.py
#
# Copy directories into place to prepare for publishing biicode project
#
# See /LICENCE.md for Copyright information
"""Place a symbolic link of pandoc in a writable directory in PATH."""

import errno

import os


def _move_directories_ignore_errors(directories, src, dst):
    """Move specified directories from :src: to :dst: ignoring errors."""
    for name in directories:
        try:
            os.rename(os.path.join(src, name),
                      os.path.join(dst, name))
        except OSError as error:
            if error.errno != errno.ENOENT:
                raise error


_BII_LAYOUT = [
    "bii",
    "bin",
    "lib",
    "blocks",
    "build"
]


def _get_bii_container(cont, util, shell):
    """Get pre-installed bii installation."""
    return cont.fetch_and_import("setup/project/configure_bii.py").run(cont,
                                                                       util,
                                                                       shell,
                                                                       None)


def _get_python_container(cont, util, shell):
    """Get python container pertaining to biicode installation."""
    configure_python = "setup/project/configure_python.py"
    py_ver = util.language_version("python2")
    return cont.fetch_and_import(configure_python).run(cont,
                                                       util,
                                                       shell,
                                                       py_ver)


def _set_up_bii_installation(cont, util, bii_destination):
    """Relocate the bii installation."""
    try:
        os.makedirs(os.path.dirname(bii_destination))
    except OSError as error:
        if error.errno != errno.EEXIST:
            raise error

    configure_bii = "setup/project/configure_bii.py"

    with _get_python_container(cont, util, None).activated(util):
        cont.fetch_and_import(configure_bii).run_installer(cont,
                                                           util,
                                                           util.execute,
                                                           bii_destination)
        python_binary = util.which("python")

    # Open the bii binary and re-write the shebang to
    # container the relative path to the python interpreter
    # from where we are now.
    with open(os.path.join(bii_destination, "bin", "bii"),
              "r+") as bii_binary_file:
        bii_binary_lines = bii_binary_file.readlines()
        bii_binary_lines[0] = "#!{}".format(os.path.relpath(python_binary))
        bii_binary_file.seek(0)
        bii_binary_file.write("\n".join(bii_binary_lines))


def run(cont, util, shell, argv=None):
    """Place a symbolic link of pandoc in a writable directory in PATH."""
    del argv

    cont.fetch_and_import("deploy/project/deploy.py").run(cont,
                                                          util,
                                                          shell)

    with util.Task("""Preparing for deployment to biicode"""):
        if os.environ.get("CI", None):
            build = cont.named_cache_dir("cmake-build", ephemeral=False)
            _move_directories_ignore_errors(_BII_LAYOUT, build, os.getcwd())

            if not util.which("bii") or True:
                path = os.path.dirname(util.find_usable_path_in_homedir(cont))
                with util.Task("""Installing bii to """ + path):
                    _set_up_bii_installation(cont, util, path)
