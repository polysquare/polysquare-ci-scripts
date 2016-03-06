# /ciscripts/setup/project/setup.py
#
# The main setup script to bootstrap and set up a generic project.
#
# See /LICENCE.md for Copyright information
"""The main setup script to bootstrap and set up a generic project."""

import argparse


def _prepare_project_deployment(cont, util, py_util, py_cont):
    """Install travis-bump-version, necessary for deployment on any project."""
    with util.Task("""Installing version bumper"""):
        with py_cont.activated(util):
            py_util.pip_install(cont, util, "travis-bump-version>=0.1.7")


def _get_python_container(cont, util, shell):
    """Get python container to install linters into."""
    config_python = "setup/project/configure_python.py"
    py_ver = util.language_version("python3")

    return cont.fetch_and_import(config_python).run(cont,
                                                    util,
                                                    shell,
                                                    py_ver)


def _get_ruby_container(cont, util, shell):
    """Get ruby container to run linters in."""
    config_ruby = "setup/project/configure_ruby.py"
    rb_ver = util.language_version("ruby")
    return cont.fetch_and_import(config_ruby).run(cont,
                                                  util,
                                                  shell,
                                                  rb_ver)


def _install_markdownlint(cont, util, rb_cont):
    """Install markdownlint into this container."""
    with util.Task("""Installing markdownlint"""):
        rb_util = cont.fetch_and_import("ruby_util.py")
        with rb_cont.activated(util):
            util.where_unavailable("mdl",
                                   rb_util.gem_install,
                                   cont,
                                   rb_cont,
                                   util,
                                   "mdl",
                                   instant_fail=True,
                                   path=rb_cont.executable_path())


def run(cont, util, shell, argv=None):
    """Install everything necessary to test a generic project.

    This script installs ruby 2.1 and python 2.7 as well as
    markdownlint and polysquare-generic-file-linter. It provides actions
    to check every file in a directory for the polysquare style guide.
    """
    result = util.already_completed("_POLYSQUARE_SETUP_GENERIC_PROJECT")
    if result is not util.NOT_YET_COMPLETED:
        return result

    with util.Task("""Setting up generic project"""):
        parser = argparse.ArgumentParser(description="""Set up project""")
        parser.add_argument("--no-mdl",
                            help="""Do not install markdownlint""",
                            action="store_true")
        parse_result, _ = parser.parse_known_args(argv or list())

        py_util = cont.fetch_and_import("python_util.py")
        py_cont = _get_python_container(cont, util, shell)
        rb_cont = _get_ruby_container(cont, util, shell)

        if not parse_result.no_mdl:
            _install_markdownlint(cont, util, rb_cont)

        with util.Task("""Installing polysquare style guide linter"""):
            with py_cont.activated(util):
                py_util.pip_install(cont,
                                    util,
                                    "polysquare-generic-file-linter>=0.1.1",
                                    instant_fail=True)

        util.prepare_deployment(_prepare_project_deployment,
                                cont,
                                util,
                                py_util,
                                py_cont)

        meta_container = util.make_meta_container((py_cont, rb_cont))
        util.register_result("_POLYSQUARE_SETUP_GENERIC_PROJECT",
                             meta_container)
        return meta_container
