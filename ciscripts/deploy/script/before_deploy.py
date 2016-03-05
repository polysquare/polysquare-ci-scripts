# /ciscripts/deploy/script/before_deploy.py
#
# Writes a script in the project directory called ./deploy which
# invokes the specified deploy script on the command line.
#
# See /LICENCE.md for Copyright information
"""Writes a script which can be called immediately at the deploy step."""

import os


def run(cont, util, shell, argv=None):
    """Entry point for before_deploy.

    All arguments, including the deploy script specified, are passed
    as options to python when invoking the bootstrap script.
    """
    del shell
    del util

    with open("travis-deploy", "w") as travis_deploy_script_file:
        bootstrap_script = cont.script_path("bootstrap.py").fs_path
        bootstrap_components = bootstrap_script.split(os.path.sep)
        scripts_path = os.path.sep.join(bootstrap_components[:-2])
        travis_deploy_script_file.write("#!/bin/bash\n"
                                        "python {bootstrap} -d "
                                        " {container} -r "
                                        " {scripts_path} -s {argv}"
                                        "".format(bootstrap=bootstrap_script,
                                                  container=cont.path(),
                                                  scripts_path=scripts_path,
                                                  argv=" ".join(argv)))
