# /ciscripts/ruby_util.py
#
# Ruby related utility functions.
#
# See /LICENCE.md for Copyright information
"""Ruby related utility functions."""

import fnmatch

import os

import re

import subprocess


_KNOWN_RUBY_INSTALLATIONS = dict()


# suppress(invalid-name)
def get_ruby_version_from_specified(ruby_executable, precision):
    """Get python version at precision from specified ruby_executable."""
    output = subprocess.Popen([ruby_executable, "--version"],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).communicate()
    version = "".join([o.decode() for o in output])
    version = ".".join(version.split(" ")[1].split(".")[0:precision]).strip()
    return re.compile(r"([0-9\.]+)").match(version).group(1)


def discover_rubies():
    """Search PATH for ruby installations and return as dictionary.

    Each key is a ruby version and the value corresponds to the location
    of that ruby installation on disk.
    """
    if len(_KNOWN_RUBY_INSTALLATIONS.keys()):
        return _KNOWN_RUBY_INSTALLATIONS

    for path_component in os.environ.get("PATH", "").split(os.pathsep):
        try:
            dir_contents = os.listdir(path_component)
        except OSError:
            continue

        candidates = set()
        candidates |= set(fnmatch.filter(dir_contents, "ruby"))
        candidates |= set(fnmatch.filter(dir_contents, "ruby.exe"))

        # Make everything absolute again, remove symlinks
        candidates = set([os.path.join(path_component, c) for c in candidates])
        candidates = set([p for p in candidates if not os.path.islink(p)])

        _KNOWN_RUBY_INSTALLATIONS.update({
            get_ruby_version_from_specified(p, 3): p for p in candidates
        })

    return _KNOWN_RUBY_INSTALLATIONS


def gem_install(container, rb_container, util, *args, **kwargs):
    """Install package using gem, specified in args.

    We automatically add the --conservative --no-ri --no-rdoc options
    to speed up install time.
    """
    return util.execute(container,
                        util.long_running_suppressed_output(),
                        "gem",
                        "install",
                        "--conservative",
                        "--no-ri",
                        "--no-rdoc",
                        "--bindir",
                        rb_container.gem_binary_directory(),
                        *args,
                        **kwargs)
