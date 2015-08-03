# /ciscripts/ruby_util.py
#
# Ruby related utility functions.
#
# See /LICENCE.md for Copyright information
"""Ruby related utility functions."""


def gem_install(container, util, *args, **kwargs):
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
                        *args,
                        **kwargs)
