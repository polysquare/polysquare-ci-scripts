# /ciscripts/util.py
#
# General utility functions which are made available to all other scripts
#
# See /LICENCE.md for Copyright information
"""General utility functions which are made available to all other scripts."""

import fnmatch

import os

import platform

import stat

import subprocess

import sys

import threading


from contextlib import contextmanager

try:
    from Queue import Queue, Empty
except ImportError:
    # suppress(F811,E301,E101,F401,import-error,unused-import)
    from queue import Queue, Empty


PRINT_MESSAGES_TO = None


def print_message(message):
    """Print to PRINT_MESSAGES_TO."""
    message = message.encode(sys.getdefaultencoding(),
                             "replace").decode("utf-8")
    if PRINT_MESSAGES_TO:
        PRINT_MESSAGES_TO.write(message)
        PRINT_MESSAGES_TO.flush()
    else:
        sys.stderr.write(message)


def overwrite_environment_variable(parent, key, value):
    """Overwrite environment variables in current and parent context."""
    if value is not None:
        os.environ[key] = str(value)
    elif os.environ.get(key, None):
        del os.environ[key]

    parent.overwrite_environment_variable(key, value)


def prepend_environment_variable(parent, key, value):
    """Prepend value to the environment variable list in key."""
    env_sep = ";" if platform.system() == "Windows" else ":"
    os.environ[key] = "{0}{1}{2}".format(str(value),
                                         env_sep,
                                         os.environ.get(key) or "")
    parent.prepend_environment_variable(key, value)


# There's no way we can make this function name shorter without making
# it inconsistent with other names or loosing descriptiveness
#
# suppress(invalid-name)
def remove_from_environment_variable(parent, key, value):
    """Remove value from an environment variable list in key."""
    env_sep = ";" if platform.system() == "Windows" else ":"
    environ_list = maybe_environ(key).split(env_sep)
    os.environ[key] = env_sep.join([i for i in environ_list if i != value])

    # See http://stackoverflow.com/questions/370047/
    parent.remove_from_environment_variable(key, value)


def define_command(parent, name, command):
    """Define a function called name which runs command in the parent scope."""
    parent.define_command(name, command)


def maybe_environ(key):
    """Return environment variable for key, or an empty string."""
    try:
        return os.environ[key]
    except KeyError:
        return ""


def _match_all(abs_dir, matching, not_matching):
    """Return all directories in abs_dirs matching all expressions."""
    for expression in matching:
        if not fnmatch.fnmatch(abs_dir, expression):
            return False

    for expression in not_matching:
        if fnmatch.fnmatch(abs_dir, expression):
            return False

    return True


def apply_to_files(func, tree_node, matching=None, not_matching=None):
    """Apply recursively to all files in tree_node.

    Function will be applied to all filenames matching 'matching', but
    will not be applied to any file matching matching 'not_matching'.
    """
    result = []
    matching = matching or list()
    not_matching = not_matching or list()
    for root, _, filenames in os.walk(tree_node):
        abs_files = [os.path.join(root, f) for f in filenames]
        result.extend([func(f) for f in abs_files if _match_all(f,
                                                                matching,
                                                                not_matching)])

    return result


def apply_to_directories(func, tree_node, matching=None, not_matching=None):
    """Apply recursively to all directories in tree_node.

    Function will be applied to all filenames matching 'matching', but
    will not be applied to any file matching matching 'not_matching'.
    """
    result = []
    matching = matching or list()
    not_matching = not_matching or list()
    for root, directories, _, in os.walk(tree_node):
        abs_dirs = [os.path.join(root, d) for d in directories]
        result.extend([func(d) for d in abs_dirs if _match_all(d,
                                                               matching,
                                                               not_matching)])

    return result


class IndentedLogger(object):

    """A logger that writes to sys.stderr with indents.

    IndentedLogger follows some rules when logging to ensure that
    output is formatted in the way that you expect.

    When it is used as a context manager, the indent level increases by one,
    and all subsequent output is logged on the next indentation level.

    The logger also ensures that initial and parting newlines are printed
    in the right place.
    """

    _indent_level = 0
    _printed_on_secondary_indents = False

    @staticmethod  # suppress(PYC90)
    def __enter__():
        """Increase indent level and return self."""
        IndentedLogger._indent_level += 1
        return IndentedLogger

    @staticmethod  # suppress(PYC90)
    def __exit__(exc_type, value, traceback):
        """Decrease indent level.

        If we printed anything whilst we were indented on more than level
        zero, then print a trailing newline, to separate out output sets.
        """
        del exc_type
        del value
        del traceback

        IndentedLogger._indent_level -= 1

        if (IndentedLogger._indent_level == 0 and
                IndentedLogger._printed_on_secondary_indents):
            print_message("\n")
            IndentedLogger._printed_on_secondary_indents = False

    @staticmethod
    def message(message_to_print):
        """Print a message, with a pre-newline, splitting on newlines."""
        if IndentedLogger._indent_level > 0:
            IndentedLogger._printed_on_secondary_indents = True

        indent = IndentedLogger._indent_level * "    "
        formatted = message_to_print.replace("\r", "\r" + indent)
        formatted = formatted.replace("\n", "\n" + indent)
        print_message(formatted)

    @staticmethod
    def dot():
        """Print a dot, just for status."""
        print_message(".")


# This is intended to be used as a context manager, so it doesn't
# need to have public methods.
#
# suppress(too-few-public-methods)
class Task(object):

    """A message for a task to being performed.

    Use this as a context manager to print a message and then perform
    a task within that context. Nested tasks get nested indents.
    """

    nest_level = 0

    def __init__(self, description):
        """Initialize this Task."""
        super(Task, self).__init__()

        indicator = "==>" if Task.nest_level == 0 else "..."
        IndentedLogger.message("\n{0} {1}".format(indicator, description))

    def __enter__(self):  # suppress(no-self-use)
        """Increment active nesting level."""
        Task.nest_level += 1
        IndentedLogger.__enter__()

    def __exit__(self, exec_type, value, traceback):  # suppress(no-self-use)
        """Decrement the active nesting level."""
        IndentedLogger.__exit__(exec_type, value, traceback)
        Task.nest_level -= 1


@contextmanager
def thread_output(*args, **kwargs):
    """Get return value of thread as queue, joining on end."""
    return_queue = Queue()
    kwargs["args"] = (kwargs["args"] or tuple()) + (return_queue, )
    thread = threading.Thread(*args, **kwargs)
    thread.start()
    yield return_queue
    thread.join()


def output_on_fail(process, outputs):
    """Capture output, displaying it if the process fails."""
    def reader(handle, input_queue):
        """Thread which reads handle, until EOF."""
        input_queue.put(handle.read())

    with thread_output(target=reader, args=(outputs[0], )) as stdout_queue:
        with thread_output(target=reader,
                           args=(outputs[1], )) as stderr_queue:
            stdout = stdout_queue.get()
            stderr = stderr_queue.get()

    status = process.wait()

    if status != 0:
        IndentedLogger.message("\n")
        IndentedLogger.message(stdout.decode("utf-8"))
        IndentedLogger.message(stderr.decode("utf-8"))

    return status


def long_running_suppressed_output(dot_timeout=10):
    """Print dots in a separate thread until our process is done."""
    def strategy(process, outputs):
        """Partially applied strategy to be passed to execute."""
        def print_dots(status_queue):
            """Print a dot every dot_timeout seconds."""
            while True:
                # Exit when something gets written to the pipe
                try:
                    status_queue.get(True, dot_timeout)
                    return
                except Empty:
                    IndentedLogger.dot()

        status_queue = Queue()
        dots_thread = threading.Thread(target=print_dots,
                                       args=(status_queue, ))
        dots_thread.start()

        try:
            status = output_on_fail(process, outputs)
        finally:
            status_queue.put("done")
            dots_thread.join()

        return status

    return strategy


def running_output(process, outputs):
    """Show output of process as it runs."""
    state = type("State",
                 (object, ),
                 {
                     "printed_message": False,
                     "read_first_byte": False
                 })

    def output_printer(file_handle):
        """Thread that prints the output of this process."""
        character = bytearray()
        while True:
            character += file_handle.read(1)
            try:
                if character:
                    if not state.read_first_byte:
                        state.read_first_byte = True

                        if character != "\n":
                            IndentedLogger.message("\n")

                    # If this fails, then we will just read further characters
                    # until the decode succeeds.
                    IndentedLogger.message(character.decode("utf-8"))
                    state.printed_message = True
                    character = bytearray()
                else:
                    return
            except UnicodeDecodeError:
                continue

    stdout = threading.Thread(target=output_printer, args=(outputs[0], ))

    stdout.start()
    stderr_lines = list(outputs[1])

    try:
        status = process.wait()
    finally:
        stdout.join()

    for line in stderr_lines:
        IndentedLogger.message(line.decode("utf-8"))
        state.printed_message = True

    if state.printed_message:
        print_message("\n")

    return status


@contextmanager
def close_file_pair(pair):
    """Close the pair of files on exit."""
    try:
        yield pair
    finally:
        pair[0].close()
        pair[1].close()


@contextmanager
def in_dir(path):
    """Execute statements in this context in path."""
    cwd = os.getcwd()
    os.chdir(path)

    try:
        yield
    finally:
        os.chdir(cwd)


def _process_shebang(args):
    """Process any shebangs.

    This needs to be done by us, because it is not done automatically
    on some operating systems, like Windows.
    """
    # If the first argument's extension is in PATHEXT then we can just
    # execute it directly - the operating system will know what to do.
    for ext in os.environ.get("PATHEXT", "").split(os.pathsep):
        if os.path.splitext(args[0])[1] == ext:
            return args

    path_to_exec = which(args[0])

    if path_to_exec is None:
        msg = """Can't find binary {0} in PATH""".format(args[0])
        raise RuntimeError(msg)

    try:
        with open(path_to_exec, "rt") as exec_file:
            if exec_file.read(2) == "#!":
                shebang = exec_file.readline().strip().replace("\n", "")
                shebang_args = shebang.split(" ")
                shebang_args = ([os.path.basename(shebang_args[0])] +
                                shebang_args[1:])
                return shebang_args + [path_to_exec] + list(args[1:])
    # If we couldn't decode the file, it is probably a binary file, so
    # just execute it directly.
    except UnicodeDecodeError:  # suppress(pointless-except)
        pass

    return args


def execute(container, output_strategy, *args, **kwargs):
    """A thin wrapper around subprocess.Popen.

    This class encapsulates a single command. The first argument to the
    constructor specifies how this command's output should be handled
    (either suppressed, or forwarded to stderr). Remaining arguments
    will be passed to Popen.
    """
    env = os.environ.copy()

    if kwargs.get("env"):
        env.update(kwargs["env"])

    try:
        cmd = _process_shebang(args)

        process = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   env=env)
    except OSError as error:
        raise Exception(u"""Failed to execute """
                        u"""{0} - {1}""".format(" ".join(cmd), str(error)))

    with close_file_pair((process.stdout, process.stderr)) as outputs:
        status = output_strategy(process, outputs)

        instant_fail = kwargs.get("instant_fail") or False

        if status != 0:
            IndentedLogger.message(u"""!!! Process {0}\n""".format(args[0]))
            for arg in args[1:]:
                IndentedLogger.message(u"""!!!         {0}\n""".format(arg))
            IndentedLogger.message(u"""!!! failed with {0}\n""".format(status))
            container.note_failure(instant_fail)

        return status


def which(executable):
    """Full path to executable."""
    def is_executable(path):
        """True if path exists and is executable."""
        return (os.path.exists(path) and
                not os.path.isdir(path) and
                os.access(path, os.F_OK | os.X_OK))

    def normalize(path):
        """Return canonical case-normalized path."""
        return os.path.normcase(os.path.realpath(path))

    def path_list():
        """Get executable path list."""
        return (os.environ.get("PATH") or os.defpath).split(os.pathsep)

    def pathext_list():
        """Get list of extensions to automatically search."""
        return (os.environ.get("PATHEXT") or "").split(os.pathsep)

    seen = set()

    for path in [normalize(p) for p in path_list()]:
        if path not in seen:
            for ext in [""] + pathext_list():
                full_path = os.path.join(path, executable) + ext
                if is_executable(full_path):
                    return full_path

            seen.add(path)

    return None


def where_unavailable(executable, function, *args, **kwargs):
    """Call function if executable is not available in PATH."""
    if which(executable) is None:
        return function(*args, **kwargs)

    return None


def prepare_deployment(function, *args, **kwargs):
    """Call function if this build is a build that will be deployed later."""
    if (os.environ.get("TRAVIS_PULL_REQUEST", None) == "false" and
            os.environ.get("TRAVIS_BRANCH", None) == "master"):
        function(*args, **kwargs)


def url_error():
    """Return class representing a failed urlopen."""
    try:
        from urllib.error import URLError
    except ImportError:
        from urllib2 import URLError

    return URLError


def url_opener():
    """Return a function that opens urls as files, performing retries."""
    from ssl import SSLError
    from socket import timeout

    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen

    def _urlopen(*args, **kwargs):
        """Open url, but set the timeout to 30 and retry a few times."""
        kwargs["timeout"] = kwargs.get("timeout", None) or 30

        if kwargs.get("retrycount"):
            retrycount = (kwargs["retrycount"] + 1)
            del kwargs["retrycount"]
        else:
            retrycount = 100

        errors = list()

        while retrycount != 0:
            try:
                return urlopen(*args, **kwargs)
            except (url_error(), SSLError, timeout) as error:
                errors.append(error)
                retrycount -= 1

        errors_string = "    \n".join([repr(e) for e in errors])
        raise url_error()(u"""Failed to open URL {0}, """
                          u"""exceeded max retries {1}. """
                          u""" Errors [{2}]\n""".format(args[0],
                                                        retrycount,
                                                        errors_string))

    return _urlopen


def get_system_identifier(container):
    """Return an identifier which contains information about the ABI."""
    system_identifier_cache_dir = container.named_cache_dir("system-id")
    system_identifier_config_guess = os.path.join(system_identifier_cache_dir,
                                                  "config.guess")

    if not os.path.exists(system_identifier_config_guess):
        domain = "http://public-travis-autoconf-scripts.polysquare.org"
        config_project = "{0}/cgit/config.git/plain".format(domain)
        with open(system_identifier_config_guess, "w") as config_guess:
            remote = url_opener()(config_project + "/config.guess")
            config_guess.write(remote.read().decode("utf-8"))

    os.chmod(system_identifier_config_guess,
             os.stat(system_identifier_config_guess).st_mode |
             stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    output = subprocess.Popen(["sh", system_identifier_config_guess],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).communicate()
    return "".join([o.decode() for o in output]).strip()
