# /test/testutil.py
#
# Some utility functions which make testing easier
#
# See /LICENCE.md for Copyright information
"""Some utility functions which make testing easier."""

import os  # suppress(PYC50)

import socket

import sys

from contextlib import contextmanager

from six import StringIO


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
    import shutil
    import tempfile

    directory = tempfile.mkdtemp(prefix, dir=parent)

    try:
        with in_dir(directory):
            yield directory
    finally:
        shutil.rmtree(directory)


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
