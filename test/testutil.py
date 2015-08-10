# /test/testutil.py
#
# Some utility functions which make testing easier
#
# See /LICENCE.md for Copyright information
"""Some utility functions which make testing easier."""

import atexit

import os

import platform

import shutil

import socket

import subprocess

import sys

import tempfile

from contextlib import contextmanager

import ciscripts.bootstrap as bootstrap
import ciscripts.util as util

from nose_parameterized import parameterized

from six import StringIO

from testtools import TestCase
from testtools.content import text_content
from testtools.matchers import Mismatch

__file__ = os.path.abspath(__file__)


# Disabled task caching in the util module - if these tests
# are run in parallel we don't want other tests to cause our
# tests to skip certain (important!) tasks or return the
# wrong container dir.
setattr(util, "_NO_TASK_CACHING", True)


class CapturedOutput(object):  # suppress(too-few-public-methods)

    """Represents the captured contents of stdout and stderr."""

    def __init__(self):
        """Initialize the class."""
        super(CapturedOutput, self).__init__()
        self.stdout = ""
        self.stderr = ""

        self._stdout_handle = None
        self._stderr_handle = None

    def __enter__(self):
        """Start capturing output."""
        self._stdout_handle = sys.stdout
        self._stderr_handle = sys.stderr

        sys.stdout = StringIO()
        sys.stderr = StringIO()

        return self

    def __exit__(self, exc_type, value, traceback):
        """Finish capturing output."""
        del exc_type
        del value
        del traceback

        sys.stdout.seek(0)
        self.stdout = sys.stdout.read()

        sys.stderr.seek(0)
        self.stderr = sys.stderr.read()

        sys.stdout = self._stdout_handle
        self._stdout_handle = None

        sys.stderr = self._stderr_handle
        self._stderr_handle = None


@contextmanager
def environment_copy():
    """Execute scope with its own os.environ.

    os.environ will be restored after the scope
    exits.
    """
    environ_copy = os.environ.copy()

    try:
        yield os.environ
    finally:
        os.environ = environ_copy


@contextmanager
def in_dir(directory):
    """Execute in the context of directory."""
    last_cwd = os.getcwd()
    os.chdir(directory)

    try:
        yield directory
    finally:
        os.chdir(last_cwd)


@contextmanager
def in_tempdir(parent, prefix):
    """Create a temporary directory as a context manager."""
    directory = tempfile.mkdtemp(prefix, dir=parent)

    try:
        with in_dir(directory):
            yield directory
    finally:
        util.force_remove_tree(directory)


@contextmanager
def server_in_tempdir(parent, prefix):
    """Create a server in a temporary directory, shutting down on exit."""
    import threading

    from six.moves import socketserver  # suppress(import-error)
    from six.moves import SimpleHTTPServer  # suppress(import-error)

    with in_tempdir(parent, prefix) as temp_dir:
        class QuietHTTPHandler(SimpleHTTPServer.SimpleHTTPRequestHandler,
                               object):

            """Custom SimpleHTTPRequestHandler, does not log messages."""

            def log_message(self, message, *args):
                """Ignore message."""
                pass

            def do_GET(self):  # suppress(N802)
                """Change into temp_dir and then chain up.

                The reason why we need to do this is that the
                underlying SimpleHTTPRequestHandler object queries the
                directory that we are currently in, as opposed to the
                directory that the server was created in. If the user
                changes their active directory (as is done in the tests)
                then requests will be resolved relative to that directory,
                which is an error.
                """
                with in_dir(temp_dir):
                    return super(QuietHTTPHandler, self).do_GET()

        server = socketserver.TCPServer(("localhost", 0), QuietHTTPHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()

        try:
            yield (temp_dir, "{0}:{1}".format(server.server_address[0],
                                              server.server_address[1]))
        finally:
            server.shutdown()
            thread.join()


def _build_http_connection(superclass, resolver):
    """Build a connection handler for superclass, resolving with resolver."""
    class Connection(superclass):  # suppress(too-few-public-methods)

        """A connection that resolves with resolver."""

        def __init__(self, *args, **kwargs):
            """Initialize this connection object."""
            superclass.__init__(self, *args, **kwargs)
            self.sock = None

        def connect(self):
            """Create a connection, resolving using resolver."""
            self.sock = socket.create_connection(resolver(self.host,
                                                          self.port),
                                                 self.timeout)

    return Connection


@contextmanager
def overridden_dns(dns_map):
    """Context manager to override the urllib HTTP DNS resolution."""
    from six.moves import http_client  # suppress(import-error)
    from six.moves import urllib  # suppress(import-error)

    def resolver(host, port):
        """If host is in dns_map, use host from map, otherwise pass through."""
        try:
            entry = dns_map[host].split(":")

            if len(entry) == 1:
                return (entry[0], port)
            else:
                assert len(entry) == 2
                return (entry[0], entry[1])

        except KeyError:
            return (host, port)

    http_connection = _build_http_connection(http_client.HTTPConnection,
                                             resolver)
    https_connection = _build_http_connection(http_client.HTTPSConnection,
                                              resolver)

    http_hnd = type("HTTPHandler",
                    (urllib.request.HTTPHandler, object),
                    {"http_open": lambda s, r: s.do_open(http_connection, r)})
    https_hnd = type("HTTPHandler",
                     (urllib.request.HTTPSHandler, object),
                     {"https_open": lambda s, r: s.do_open(https_connection,
                                                           r)})

    custom_opener = urllib.request.build_opener(http_hnd, https_hnd)
    urllib.request.install_opener(custom_opener)

    try:
        yield
    finally:
        urllib.request.install_opener(urllib.request.build_opener())


class IsInSubdirectoryOf(object):  # suppress(too-few-public-methods)

    """Match if a path is a subdirectory of the specified path."""

    def __init__(self, path):
        """Initialize mather for this path."""
        super(IsInSubdirectoryOf, self).__init__()
        self._path = path

    def __str__(self):
        """Represent matcher as string."""
        return "IsInSubdirectoryOf({0})".format(repr(self._path))

    def match(self, candidate):
        """Return Mismatch if candidate is not in a subdirectory of path."""
        if not candidate:
            return Mismatch("""None passed to match""")

        path = self._path
        if os.path.commonprefix([os.path.realpath(path).lower(),
                                 os.path.realpath(candidate).lower()]):
            return None
        else:
            return Mismatch("{0} is not in a subdir of {1}".format(candidate,
                                                                   path))


class SubprocessExitWithMismatch(object):

    """Detail of a SubprocessExitsWith mismatch."""

    # suppress(too-many-arguments)
    def __init__(self, popen_command, code, expected, stdout, stderr):
        """Initialize this mismatch detail object."""
        super(SubprocessExitWithMismatch, self).__init__()

        command = " ".join(popen_command)
        self._msg = "{0} exited with {1}, but expected {2}".format(command,
                                                                   code,
                                                                   expected)
        self._details = {
            "Output": text_content(stdout),
            "Errors": text_content(stderr)
        }

    def describe(self):
        """Return message."""
        return self._msg

    def get_details(self):
        """Return details."""
        return self._details


class SubprocessExitsWith(object):  # suppress(too-few-public-methods)

    """Match if the subprocess to be executed exits with the expected code."""

    def __init__(self, expected_code):
        """Initialize matcher for this expected code."""
        super(SubprocessExitsWith, self).__init__()
        self._expected_code = expected_code

    def __str__(self):
        """Convert matcher to string."""
        return "SubprocessExitsWith({0})".format(self._expected_code)

    def match(self, subprocess_args):
        """Fail if subprocess exits with unexpected code."""
        process = subprocess.Popen(subprocess_args,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

        code = process.wait()
        if code != self._expected_code:
            return SubprocessExitWithMismatch(subprocess_args,
                                              code,
                                              self._expected_code,
                                              process.stdout.read().decode(),
                                              process.stderr.read().decode())


class CIScriptExitsWith(object):  # suppress(too-few-public-methods)

    """Match if the specified ci-script runs with its arguments."""

    def __init__(self, expected_status, container, util_mod, *args, **kwargs):
        """Initialize matcher with the arguments we run the script with."""
        super(CIScriptExitsWith, self).__init__()
        self._expected_status = expected_status
        self._args = args
        self._kwargs = kwargs
        self._container = container
        self._util = util_mod

    def __str__(self):
        """Represent this matcher as a string."""
        return "CIScriptExitsWith({0})".format(", ".join(self._args))

    def match(self, script):
        """Match if this script runs successfully."""
        captured_output = CapturedOutput()
        assert self._container.return_code() == 0
        with captured_output:
            with environment_copy():
                run_args = [
                    self._container,
                    self._util,
                    None,
                    list(self._args)
                ]
                run_kwargs = self._kwargs
                self._container.fetch_and_import(script).run(*run_args,
                                                             **run_kwargs)

        result = self._container.return_code()
        if result != self._expected_status:
            return SubprocessExitWithMismatch(["python", script] +
                                              list(self._args),
                                              result,
                                              self._expected_status,
                                              captured_output.stdout,
                                              captured_output.stderr)


def format_with_args(*args):
    """Return a function that formats a docstring."""
    def formatter(func, _, params):
        """Return formatted docstring with argument numbers in args."""
        pa = params.args
        format_args = [pa[i] for i in range(0, len(pa)) if i in args]

        return func.__doc__.format(*format_args)

    return formatter

_ROOT = os.path.abspath(os.path.join(os.path.dirname(bootstrap.__file__),
                                     ".."))
WHICH_SCRIPT = ("import sys;sys.path.append('" + _ROOT.replace("\\",
                                                               "/") + "');"
                "import ciscripts.util;assert ciscripts.util.which('{0}')")


def _copytree_ignore_notfound(src, dst):
    """Copy an entire directory tree.

    This is effectively a workaround for situations where shutil.copytree
    is unable to copy some files. Just shell out to rsync, as rsync
    usually always gets it right in complicated cases.

    Where rsync isn't available, then we'll need to fallback to shutil.
    """
    if util.which("rsync"):
        subprocess.check_call(["rsync",
                               "-az",
                               "--chmod=ugo=rwX",
                               src + os.path.sep,
                               dst + os.path.sep])
    else:
        try:
            shutil.copytree(src, dst)
        except shutil.Error:  # suppress(pointless-except)
            pass


def copy_scripts_to_directory(target):
    """Utility method to copy CI script to current directory.

    They will be located at /ciscripts/.
    """
    parent = os.path.realpath(os.path.join(os.path.dirname(__file__),
                                           ".."))
    assert "ciscripts" in os.listdir(parent)

    shutil.copytree(os.path.join(parent, "ciscripts"),
                    os.path.join(target, "ciscripts"))


def acceptance_test_for(project_type, expected_programs):
    """Generate acceptance test class for :project_type:.

    Includes tests to ensure that :expected_programs: are
    installed in the container.
    """
    class AcceptanceTestForProject(TestCase):

        """Test cases for setting up a project container."""

        def __init__(self, *args, **kwargs):
            """Initialize the instance attributes for this test case."""
            super(AcceptanceTestForProject, self).__init__(*args, **kwargs)
            self.project_dir = None

        @contextmanager
        def in_parent_context(self, command):
            """Get script to run command in parent context.

            The 'parent context' in this case is a shell script where the
            standard output of the container's setup script has been evaluated,
            eg, all environment variables are exported.
            """
            directory = tempfile.mkdtemp(prefix=os.path.join(os.getcwd(),
                                                             "parent_script"))

            script_path = os.path.abspath(os.path.join(directory,
                                                       "script.ps1"))
            script_path_for_shell = os.path.abspath(script_path)
            if platform.system() == "Windows":
                shell = ["powershell", "-ExecutionPolicy", "Bypass"]
                script_path_for_shell = "\"{}\"".format(script_path_for_shell)
            else:
                shell = ["bash"]

            script = ("{cls.setup_container_output.stdout}"
                      "{command}").format(cls=self.__class__, command=command)

            try:
                with util.in_dir(directory):
                    with open(script_path, "w") as script_file:
                        script_file.write(script)

                    # powershell requires that paths with spaces be
                    # quoted, even when passed as part of the command line
                    # arguments, so we use script_path here as it is formatted
                    # above
                    yield shell + [script_path_for_shell]
            finally:
                script_file.close()
                util.force_remove_tree(directory)

        @classmethod
        def setup_script(cls):
            """Setup script for this acceptance test fixture."""
            return "setup/cmake/setup.py"

        @classmethod
        def setUpClass(cls):  # suppress(N802)
            """Call container setup script."""
            temp_dir_prefix = "{}_acceptance_test".format(project_type)
            cls.container_temp_dir = tempfile.mkdtemp(dir=os.getcwd(),
                                                      prefix=temp_dir_prefix)
            atexit.register(util.force_remove_tree, cls.container_temp_dir)
            cls._environ_backup = os.environ.copy()

            if os.environ.get("CONTAINER_DIR"):
                container_dir = os.environ["CONTAINER_DIR"]
                util.force_remove_tree(cls.container_temp_dir)
                _copytree_ignore_notfound(container_dir,
                                          cls.container_temp_dir)

                # Delete ciscripts in the copied container
                try:
                    util.force_remove_tree(os.path.join(cls.container_temp_dir,
                                                        "_scripts"))
                except (shutil.Error, OSError):  # suppress(pointless-except)
                    pass

            scripts_directory = os.path.join(cls.container_temp_dir,
                                             "_scripts")
            copy_scripts_to_directory(scripts_directory)

            setup_script = "setup/{type}/setup.py".format(type=project_type)
            cls.setup_container_output = CapturedOutput()

            extra_args = list()

            # Don't install mdl on AppVeyor - installing any gem is far
            # too slow and will cause the job to time out.
            if os.environ.get("APPVEYOR", None):
                extra_args.append("--no-mdl")

            with cls.setup_container_output:
                if platform.system() == "Windows":
                    shell = bootstrap.construct_parent_shell("powershell",
                                                             sys.stdout)
                else:
                    shell = bootstrap.construct_parent_shell("bash",
                                                             sys.stdout)

                kwargs = {
                    "scripts_directory": scripts_directory
                }
                cls.container = bootstrap.ContainerDir(shell,
                                                       cls.container_temp_dir,
                                                       **kwargs)
                cls.util = cls.container.fetch_and_import("util.py")

                # Look up where to print messages to at the time messages
                # are printed, such that we get the redirected messages
                # from sys.stderr
                cls.util.PRINT_MESSAGES_TO = None

                setup_module = cls.container.fetch_and_import(setup_script)
                cls.lang_container = setup_module.run(cls.container,
                                                      util,
                                                      shell,
                                                      extra_args)

                assert cls.container.return_code() == 0

        @classmethod
        def tearDownClass(cls):  # suppress(N802)
            """Remove container."""
            os.environ = cls._environ_backup
            util.force_remove_tree(cls.container_temp_dir)

        def _get_project_template(self):  # suppress(no-self-use)
            """Get template of project type from /sample."""
            parent = os.path.realpath(os.path.join(os.path.dirname(__file__),
                                                   ".."))
            assert "sample" in os.listdir(parent)
            assert project_type in os.listdir(os.path.join(parent, "sample"))
            return os.path.join(parent, "sample", project_type)

        def setUp(self):  # suppress(N802)
            """Create a copy of and enter sample project directory."""
            super(AcceptanceTestForProject, self).setUp()

            # Create copy of the sample project
            current_directory = os.getcwd()
            temp_dir_prefix = "{}_project_copy".format(project_type)
            project_copy_temp_dir = tempfile.mkdtemp(dir=current_directory,
                                                     prefix=temp_dir_prefix)
            self.addCleanup(util.force_remove_tree, project_copy_temp_dir)
            self.project_dir = os.path.join(project_copy_temp_dir,
                                            project_type)

            shutil.copytree(self._get_project_template(), self.project_dir)
            os.chdir(self.project_dir)
            self.addCleanup(os.chdir, current_directory)

            self.__class__.container.reset_failure_count()

        _PROGRAMS = [
            "polysquare-generic-file-linter"
        ]

        if not os.environ.get("APPVEYOR", None):
            _PROGRAMS.append("mdl")

        _PROGRAMS.extend(expected_programs)

        @parameterized.expand(_PROGRAMS, testcase_func_doc=format_with_args(0))
        def test_program_is_available_in_python_script(self, program):
            """Executable {0} is available after running setup."""
            temp_dir = self.__class__.container_temp_dir
            with self.__class__.lang_container.activated(util):
                self.assertThat(util.which(program),
                                IsInSubdirectoryOf(temp_dir))

    return AcceptanceTestForProject
