# /ciscripts/deploy/bii/deploy.py
#
# Copy directories into place to prepare for publishing biicode project
#
# See /LICENCE.md for Copyright information
"""Place a symbolic link of pandoc in a writable directory in PATH."""

import errno

import os

import shutil


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
    return cont.fetch_and_import("setup/project/configure_bii.py").get(cont,
                                                                       util,
                                                                       shell,
                                                                       None)


def _get_python_container(cont, util, shell):
    """Get python container pertaining to biicode installation."""
    configure_python = "setup/project/configure_python.py"
    py_ver = util.language_version("python2")
    return cont.fetch_and_import(configure_python).get(cont,
                                                       util,
                                                       shell,
                                                       py_ver)


def _set_up_bii_installation(bii_binary_source,
                             python_binary_source,
                             bii_binary_destination,
                             biicode_module_source,
                             biicode_module_destination):
    """Relocate the bii installation."""
    try:
        os.makedirs(os.path.dirname(bii_binary_destination))
    except OSError as error:
        if error.errno != errno.EEXIST:
            raise error

    shutil.copy(bii_binary_source, bii_binary_destination)
    shutil.copytree(biicode_module_source,
                    os.path.join(biicode_module_destination, "biicode"))

    # Open the bii binary and re-write the shebang to
    # container the relative path to the python interpreter
    # from where we are now.
    with open(bii_binary_destination, "r+") as bii_binary_file:
        bii_binary_lines = bii_binary_file.readlines()
        bii_binary_lines[0] = "#!{}".format(python_binary_source)
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

            if not util.which("bii"):
                path = util.find_usable_path_in_homedir(cont)
                bii_cont = _get_bii_container(cont, util, shell)
                py_cont = _get_python_container(cont, util, shell)
                python_binary = os.path.join(py_cont.executable_path(),
                                             "python")
                with bii_cont.activated(util):
                    bii_binary = util.which("bii")
                    binary_dir = os.path.dirname(bii_binary)
                    biicode_module = os.path.abspath(os.path.join(binary_dir,
                                                                  "..",
                                                                  "biicode"))
                destination = os.path.join(path, "bii")
                with util.Task("""Copying bii binary from """
                               """{0} to {1}.""".format(bii_binary,
                                                        destination)):
                    _set_up_bii_installation(bii_binary,
                                             os.path.relpath(python_binary),
                                             destination,
                                             biicode_module,
                                             path)
