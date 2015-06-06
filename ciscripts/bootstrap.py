#!/usr/bin/env python
# /ciscripts/bootstrap.py
#
# Initial functions and classes necessary to create the test container
# and start loading other scripts.
#
# See /LICENCE.md for Copyright information
"""Create the test container and start loading other scripts."""

import abc

import argparse

import errno

import imp

import importlib

import os

import platform

import re

import shutil

import sys

from collections import (defaultdict,
                         namedtuple)

from contextlib import closing, contextmanager

try:
    from urllib.request import urlopen
    from urllib.error import URLError
except ImportError:
    from urllib2 import urlopen
    from urllib2 import URLError


def force_mkdir(directory):
    """Recursively make all directories, ignores existing directories."""
    try:
        os.makedirs(directory)
    except OSError as error:
        if error.errno != errno.EEXIST:  # suppress(PYC90)
            raise error

    return directory


def open_and_force_mkdir(path, mode):
    """Recursively create directories for path to file and then open it."""
    force_mkdir(os.path.dirname(path))
    return open(path, mode)


class BashParentEnvironment(object):

    """A parent environment in a bash shell."""

    @staticmethod
    def _format_environment_value(value):
        """Format an environment variable value for this shell."""
        value = str(value)
        if platform.system() == "Windows":
            # Split on semicolons first
            components = value.split(os.pathsep)

            # On each component, replace anything that looks like
            # a drive letter with a unix-like drive path.
            components = [re.sub(r"^([A-Za-z]):\\",
                                 r"\\\1\\",
                                 c) for c in components]

            return ":".join(components).replace("\\", "/")

        return value

    def __init__(self, printer):
        """Initialize this parent environment with printer."""
        super(BashParentEnvironment, self).__init__()
        self._printer = printer

    def overwrite_environment_variable(self, key, value):
        """Generate and execute script to overwrite variable key."""
        if value is not None:
            value = BashParentEnvironment._format_environment_value(value)
            self._printer("export {0}=\"{1}\"".format(key, value))
        else:
            self._printer("unset {0}".format(key))

    # suppress(invalid-name)
    def remove_from_environment_variable(self, key, value):
        """Generate and execute script to remove value from key."""
        value = BashParentEnvironment._format_environment_value(value)
        script = ("export {k}=$(python -c \"print(\\\":\\\".join(["
                  "v for v in \\\"${k}\\\".split(\\\":\\\") "
                  "if v not in \\\"{v}\\\".split(\\\":\\\")]))\")")
        # There is something about the format() method on str which causes
        # pychecker to trip over when passing keyword arguments. Just
        # pass keyword arguments using the ** notation.
        script_keys = {
            "k": key,
            "v": value
        }
        script = script.format(**script_keys)
        self._printer(script)

    def prepend_environment_variable(self, key, value):
        """Generate and execute script to prepend value to key."""
        value = BashParentEnvironment._format_environment_value(value)
        script_keys = {
            "k": key,
            "v": value
        }
        script = "export {k}=\"{v}:${k}\"".format(**script_keys)
        self._printer(script)

    def define_command(self, name, command):
        """Define a function called name which runs command."""
        code = ("function %s {"
                "    %s \"$@\"\n"
                "}") % (name, command)
        self._printer(code)

    def exit(self, status):
        """Cause the shell to exit with status."""
        self._printer("exit {0}".format(status))


class PowershellParentEnvironment(object):

    """A parent environment in a bash shell."""

    def __init__(self, printer):
        """Initialize this parent environment with printer."""
        super(PowershellParentEnvironment, self).__init__()
        self._printer = printer

    def overwrite_environment_variable(self, key, value):
        """Generate and execute script to overwrite variable key."""
        if value is not None:
            self._printer("$env:{0} = \"{1}\"".format(key, value))
        else:
            self._printer("$env:{0} = \"\"".format(key))

    # suppress(invalid-name)
    def remove_from_environment_variable(self, key, value):
        """Generate and execute script to remove value from key."""
        script = ("$env:{k} = python -c \"print(';'.join(["
                  "v for v in r'$env:{k}'.split(';') "
                  "if v not in r'{v}'.split(';')]))\"")
        script_keys = {
            "k": key,
            "v": value
        }
        script = script.format(**script_keys)
        self._printer(script)

    def prepend_environment_variable(self, key, value):
        """Generate and execute script to prepend value to key."""
        script_keys = {
            "k": key,
            "v": value
        }
        script = "$env:{k} = \"{v};$env:{k}\"".format(**script_keys)
        self._printer(script)

    def define_command(self, name, command):
        """Define a function called name which runs command.

        The function will check that command's exit status and exit
        the entire script with a failure exit code if
        the subcommand failed.
        """
        code = ("function %s {"
                "    %s $args\n"
                "    $status = $?\n"
                "    If ($status -eq 0) {\n"
                "        exit 1\n"
                "    }\n"
                "}") % (name, command)
        self._printer(code)

    def exit(self, status):
        """Cause the shell to exit with status."""
        self._printer("exit {0}".format(status))


def _update_set_like_file(path, key):
    """For the file containing unique lines at :path:, add :key:.

    This function assumes that the file at :path: is a set-like file -
    it should contain one line per unique entry. :key: will be added
    if the file does not contain it already.
    """
    added_key = False
    try:
        with open(path, "r") as set_like_file:
            records = set(set_like_file.read().splitlines())
            if key not in records:
                records |= set([key])
                added_key = True
    except IOError:
        # Set added_key to True so that we write to this file
        # next time
        added_key = True
        records = set([key])

    # Only modify the file if we added a new language record, otherwise
    # this file will cause the cache to be constantly marked as
    # invalid.
    if added_key:
        with open(path, "w") as set_like_file:
            set_like_file.truncate(0)
            set_like_file.write("\n".join(list(records)))


class ContainerBase(object):

    """Base class for all language and top-level containers."""

    def __init__(self, directory):
        """Initialize a ContainerBase for this directory."""
        super(ContainerBase, self).__init__()

        self._container_dir = os.path.realpath(directory)
        self._cache_dir = force_mkdir(os.path.join(self._container_dir,
                                                   "_cache"))
        self._ephemeral_caches = os.path.join(self._cache_dir, "emphemeral")

    @staticmethod
    def _delete(node):
        """Delete node on the file system in the way you expect.

        If :node: is a directory, remove it recursively. If it is a file,
        then unlink it. If it is a symbolic link, then remove it.
        """
        try:
            if os.path.isdir(node):
                shutil.rmtree(node)
            else:
                os.unlink(node)
        except OSError as error:
            if error.errno != errno.ENOENT:   # suppress(PYC90)
                raise error

    @abc.abstractmethod
    def clean(self, util):
        """Clean out this ContainerBase.

        Remove all named caches marked as ephemeral.
        """
        if os.path.exists(self._ephemeral_caches):
            with util.Task("""Cleaning ephemeral caches"""):
                with open(self._ephemeral_caches, "r") as ephemeral_log:
                    for ephemeral_cache in ephemeral_log.readlines():
                        shutil.rmtree(os.path.join(self._cache_dir,
                                                   ephemeral_cache.strip()))

                self._delete(self._ephemeral_caches)

    def named_cache_dir(self, name, ephemeral=True):
        """Return a dir called name in the cache dir, even if it exists.

        If ephemeral is True, then wipe out this cache directory once
        the clean method is called on the container.
        """
        path = os.path.join(self._cache_dir, name)
        force_mkdir(path)

        if ephemeral:
            _update_set_like_file(self._ephemeral_caches, name)

        return path

    def path(self):
        """Return path to this container directory."""
        return self._container_dir

    @contextmanager
    def in_temp_cache_dir(self):
        """Create a temporary directory in the cache dir.

        The directory self-destructs on context exit.
        """
        import tempfile

        path = tempfile.mkdtemp(dir=self._cache_dir)

        try:
            yield path
        finally:
            try:
                self._delete(path)
            except OSError as error:
                if error.errno != errno.ENOENT:
                    raise error

ActivationKeys = namedtuple("ActivationKeys",
                            "activated version deactivate inserted")


def _keys_for_activation(language):
    """Get environment variable keys for activating language."""
    language_upper = language.upper()
    return ActivationKeys("_POLYSQUARE_ACTIVATED_{0}".format(language_upper),
                          "_POLYSQUARE_{0}_VERSION".format(language_upper),
                          "_POLYSQUARE_DEACTIVATED_%s_{key}" % language_upper,
                          "_POLYSQUARE_INSERTED_%s_{key}" % language_upper)

ActiveEnvironment = namedtuple("ActiveEnvironment", "overwrite prepend")


class LanguageBase(ContainerBase):

    """An abstract base class for a language-specific container."""

    def __init__(self, installation, language, version, parent_shell):
        """Initialize this abstract LanguageBase class for language."""
        super(LanguageBase, self).__init__(installation)
        self._language = language
        self._version = version
        self._installation = self._container_dir
        self._parent_shell = parent_shell

    @abc.abstractmethod
    def _active_environment(self, tuple_type):
        """Override and return environment variables in active state.

        This function should return environment variables in the tuple
        LanguageBase.ActiveEnvironment, which has the attributes
        'prepend' for environment variables which are intended
        to be prepended to the parent path and 'overwrite', for
        variables that should be overwritten.
        """
        return

    def activate(self, util):
        """Activate this container in both the parent and current context.

        This will set the environment using the data in _active_environment
        and create a backup of those variables so that the container can
        be deactivated later.
        """
        # Skip if this container has already been activated
        activation_keys = _keys_for_activation(self._language)
        if os.environ.get(activation_keys.activated):
            return False

        active_environment = self._active_environment(ActiveEnvironment)

        for key, value in active_environment.overwrite.items():
            backup = activation_keys.deactivate.format(key=key)
            util.overwrite_environment_variable(self._parent_shell,
                                                backup,
                                                util.maybe_environ(key))
            util.overwrite_environment_variable(self._parent_shell, key, value)

        for key, value in active_environment.prepend.items():
            inserted = activation_keys.inserted.format(key=key)
            util.overwrite_environment_variable(self._parent_shell,
                                                inserted,
                                                value)
            util.prepend_environment_variable(self._parent_shell, key, value)

        util.overwrite_environment_variable(self._parent_shell,
                                            activation_keys.activated,
                                            "1")
        util.overwrite_environment_variable(self._parent_shell,
                                            activation_keys.version,
                                            self._version)

        return True

    def deactivate(self, util):
        """Deactivate this container in both the parent and current context.

        This will look at the keys in _active_environment and use those to
        retrieve backups and restore them, effectively deactivating the
        container.
        """
        activation_keys = _keys_for_activation(self._language)
        if not os.environ.get(activation_keys.activated):
            return False

        active_environment = self._active_environment(ActiveEnvironment)

        for key in active_environment.overwrite.keys():
            backup = activation_keys.deactivate.format(key=key)
            util.overwrite_environment_variable(self._parent_shell,
                                                key,
                                                os.environ.get(backup, ""))
            util.overwrite_environment_variable(self._parent_shell,
                                                backup,
                                                None)

        for key in active_environment.prepend.keys():
            inserted = activation_keys.inserted.format(key=key)
            util.remove_from_environment_variable(self._parent_shell,
                                                  key,
                                                  os.environ[inserted])
            util.overwrite_environment_variable(self._parent_shell,
                                                inserted,
                                                None)

        util.overwrite_environment_variable(self._parent_shell,
                                            activation_keys.activated,
                                            None)
        util.overwrite_environment_variable(self._parent_shell,
                                            activation_keys.version,
                                            None)

        return True

    def executable_path(self):
        """Return executable path for this container.

        This is effectively the contents of what will be prepended to the
        PATH variable if this container is activated.
        """
        prepend = self._active_environment(ActiveEnvironment).prepend
        return prepend.get("PATH", "")

    @contextmanager
    def activated(self, util):
        """Perform actions in this context with activated container."""
        self.activate(util)
        try:
            yield
        finally:
            self.deactivate(util)

    @contextmanager
    def deactivated(self, util):
        """Perform actions in this context with deactivated container."""
        self.deactivate(util)
        try:
            yield
        finally:
            self.activate(util)


FetchedModule = namedtuple("FetchedModule", "in_scripts_dir fs_path")


def _fetch_script(info,
                  script_path,
                  domain="public-travis-scripts.polysquare.org"):
    """Download a script if it doesn't exist."""
    if not os.path.exists(info.fs_path):
        with open_and_force_mkdir(info.fs_path, "w") as scr:
            remote = "%s/%s" % (domain, script_path)
            retrycount = 100
            while retrycount != 0:
                try:
                    contents = urlopen("http://{0}".format(remote)).read()
                    scr.write(contents.decode())
                    scr.truncate()
                    retrycount = 0
                except URLError:
                    retrycount -= 1


class ContainerDir(ContainerBase):

    """A container that all scripts and other data will be stored in."""

    def __init__(self, shell, directory=None, **kwargs):
        """Initialize this container in the directory specified."""
        super(ContainerDir, self).__init__(directory)
        if kwargs.get("scripts_directory"):
            self._scripts_dir = kwargs["scripts_directory"]
            self._force_created_scripts_dir = False
        else:
            self._scripts_dir = force_mkdir(os.path.join(self._container_dir,
                                                         "_scripts"))
            # Ensure that we have a /bootstrap.py script in our
            # container.
            _fetch_script(self.script_path("bootstrap.py"), "bootstrap.py")
            self._force_created_scripts_dir = True

        sys.path = [self._scripts_dir] + sys.path

        self._languages_dir = force_mkdir(os.path.join(self._container_dir,
                                                       "_languages"))
        self._languages_record_path = os.path.join(self._languages_dir,
                                                   "record")
        self._module_cache = dict()

        # Create languages record file if it doesn't exist
        if not os.path.exists(self._languages_record_path):
            with open(self._languages_record_path, "w"):
                pass

        self._failures = 0
        self._shell = shell

    def clean(self, util):
        """Clean this container and all sub-containers."""
        super(ContainerDir, self).clean(util)

        info = namedtuple("Info", "language version")

        # Having everything on one line is nice
        #
        # suppress(invalid-name)
        with open(self._languages_record_path, "r") as f:
            containers = [info(*(c.split("-"))) for c in f.read().splitlines()]

        for info in containers:
            with util.Task("""Cleaning {0} {1} """
                           """container""".format(info.language,
                                                  info.version)):
                script = "setup/project/configure_{0}.py".format(info.language)
                ver_info = defaultdict(lambda: info.version)
                self.fetch_and_import(script).get(self,
                                                  util,
                                                  None,
                                                  ver_info).clean(util)

        with util.Task("""Cleaning up downloaded scripts"""):
            if self._force_created_scripts_dir:
                self._delete(self._scripts_dir)

    def script_path(self, relative_path):
        """Get absolute path to script specified at relative_path.

        This function first looks in the current working directory
        for a script named by :relative_path: and if it can't find
        it, it will look in its own internal scripts directory.
        """
        # First try to find the script locally in the
        # current working directory.
        fs_path = os.path.realpath(os.path.join(os.getcwd(), relative_path))

        # Next try to find it in our scripts directory, or fetch it from
        # the server which hosts all the scripts.
        if not os.path.exists(fs_path):
            fs_path = os.path.join(self._scripts_dir,
                                   "ciscripts",
                                   relative_path)
            return FetchedModule(True, fs_path)
        else:
            return FetchedModule(False, fs_path)

    # suppress(unused-function)
    def loaded_module_name(self,
                           script_path,
                           domain="public-travis-scripts.polysquare.org"):
        """Get loaded module name for :script_path:."""
        key = "{0}/{1}".format(domain, script_path)
        try:
            return self._module_cache[key].__name__
        except KeyError:
            return None

    def fetch_and_import(self,
                         script_path,
                         domain="public-travis-scripts.polysquare.org"):
        """Download a script if its not available and import it.

        This downloads the script as part of the URL path as indicated by
        script_path if it isn't already available in the specified directory.
        """
        def import_file_directly(path):
            """Import a file at :path: directly, bypassing __import__."""
            name = "local_module_" + re.sub(r"[\./]", "_", path)
            return imp.load_source(name, path)

        # First try to find the script locally in the
        # current working directory.
        info = self.script_path(script_path)
        _fetch_script(info, script_path)

        key = "{0}/{1}".format(domain, script_path)

        try:
            return self._module_cache[key]
        except KeyError:
            # We try to import the file normally first - this is useful
            # for tests where we want to be able to get coverage on those
            # files. If we can't import directly, then we need to
            # fall back to importing the file.
            fs_path = info.fs_path
            if info.in_scripts_dir:
                try:
                    name = os.path.relpath(os.path.splitext(fs_path)[0],
                                           start=self._scripts_dir)
                    name = name.replace(os.path.sep, ".")
                    self._module_cache[key] = importlib.import_module(name)
                except ImportError:
                    self._module_cache[key] = import_file_directly(fs_path)
            else:
                self._module_cache[key] = import_file_directly(fs_path)

        return self._module_cache[key]

    def language_dir(self, language):
        """Return a dir to hold installations of language."""
        path = os.path.join(self._languages_dir, language)
        force_mkdir(path)

        return path

    def note_failure(self, instant_fail):
        """Note a failure.

        If instant_fail is True, then immediately exit, also making the
        invoking shell exit too with our current exit status.
        """
        self._failures += 1

        if instant_fail:
            self._shell.exit(self._failures)
            sys.exit(self._failures)

    def reset_failure_count(self):  # suppress(unused-function)
        """Reset failure count for this container."""
        self._failures = 0

    def return_code(self):
        """Return code of this container."""
        return self._failures

    def new_container_for(self, language, version):
        """Return class to construct a sub-container from.

        Keep a note of the language and version combination that we just
        requested a new container for.
        """
        key = "{language}-{version}".format(language=language, version=version)
        _update_set_like_file(self._languages_record_path, key)

        return LanguageBase


def escaped_printer_with_character(char, file_object=None):
    """Return a function that escapes special characters with :char:."""
    def escaped_printer(to_write):
        """Print text in a format suitable for consumption by a shell."""
        # suppress(anomalous-backslash-in-string)
        to_write = to_write.replace(";", "{c};".format(c=char))
        to_write = to_write.replace("\n", ";\n") + ";\n"

        if file_object:
            file_object.write(to_write)
        else:
            sys.stdout.write(to_write)

    return escaped_printer


def construct_parent_shell(eval_output_with, print_script_to):
    """Construct a class emitting scripts compatible with eval_output_with."""
    if eval_output_with:
        environment_ctor = {
            "bash": BashParentEnvironment,
            "powershell": PowershellParentEnvironment
        }

        printers = {
            "bash": escaped_printer_with_character("\\", print_script_to),
            "powershell": escaped_printer_with_character("`",
                                                         print_script_to)
        }

        printer = printers[eval_output_with]
        return environment_ctor[eval_output_with](printer)
    else:
        return BashParentEnvironment(lambda _: None)


def main(argv):
    """Create or use an existing container and run a script.

    If -e is passed, then output which is capable of being executed
    in the shell invoking this script will be printed on the standard out. It
    is expected that the user will capture this output and evaluate it, as it
    is a mechanism for activating local language installations and retaining
    state across invocations.

    A script to evaluate from this one should be passed with -s. It should
    have a function called 'run' which takes three arguments - an object
    representing a created ContainerDir, a handle to the utilities library
    and an object representing the parent shell, where environment
    variables can be exported and other shell scripts be evaluated.
    """
    parser = argparse.ArgumentParser(description="Bootstrap CI Scripts")
    parser.add_argument("-d", "--directory",
                        type=str,
                        required=True,
                        help=("Directory to store language runtimes, "
                              "scripts and other script details in"))
    parser.add_argument("-s", "--script",
                        type=str,
                        help="Script to pass control to")
    parser.add_argument("-e", "--eval-output",
                        type=str,
                        choices=[
                            "bash",
                            "powershell"
                        ],
                        help="Evaluate output in shell")
    parser.add_argument("-p", "--print-to",
                        type=str,
                        help="Where to print output script to")
    parser.add_argument("-r", "--scripts-directory",
                        type=str,
                        help="Directory where scripts are already stored in")
    args, remainder = parser.parse_known_args(argv)

    if args.print_to:
        print_script_to = open(args.print_to, "wt")
        if args.print_to == "/dev/stdout":
            print_messages_to = sys.stderr
        else:
            print_messages_to = sys.stdout
    else:
        try:
            from io import StringIO
        except ImportError:
            from cStringIO import StringIO

        print_script_to = StringIO()
        print_messages_to = sys.stdout

    with closing(print_script_to):
        parent_shell = construct_parent_shell(args.eval_output,
                                              print_script_to)
        container = ContainerDir(parent_shell, **(vars(args)))
        util = container.fetch_and_import("util.py")
        # suppress(unused-attribute)
        util.PRINT_MESSAGES_TO = print_messages_to
        bootstrap_script = container.script_path("bootstrap.py").fs_path
        bootstrap_script_components = bootstrap_script.split(os.path.sep)
        scripts_path = os.path.sep.join(bootstrap_script_components[:-2])

        parent_shell.overwrite_environment_variable("CONTAINER_DIR",
                                                    container.path())
        parent_shell.define_command("polysquare_run",
                                    "python \"{bootstrap}\" "
                                    "-d \"{container}\" "
                                    "-r \"{scripts}\" "
                                    "-s".format(bootstrap=bootstrap_script,
                                                container=container.path(),
                                                scripts=scripts_path))
        parent_shell.define_command("polysquare_cleanup",
                                    "python \"{bootstrap}\" "
                                    "-d \"{container}\" "
                                    "-r \"{scripts}\" "
                                    "-s clean.py"
                                    "".format(bootstrap=bootstrap_script,
                                              container=container.path(),
                                              scripts=scripts_path))

        # Done, pass control to the script we're to run
        container.fetch_and_import(args.script).run(container,
                                                    util,
                                                    parent_shell,
                                                    argv=remainder)

        return container.return_code()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
