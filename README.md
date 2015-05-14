# Polysquare CI Scripts #

Polysquare CI Scripts (common to a few modules).

A redirect to the raw version of these scripts exists at
`https://public-travis-scripts.polysquare.org`. You can curl them to
a python interpreter.

    $(curl -LSs https://public-travis-scripts.polysquare.org/bootstrap.py |
      python /dev/stdin -s setup/project/setup.py)

## Status ##

| Travis CI | AppVeyor | Coverage |
|-----------|----------|----------|
|[![Travis](https://travis-ci.org/polysquare/polysquare-ci-scripts.svg?branch=master)](https://travis-ci.org/polysquare/polysquare-ci-scripts)|[![AppVeyor](https://ci.appveyor.com/api/projects/status/fink8q0jbv20xdca/branch/master?svg=true)](https://ci.appveyor.com/project/smspillaz/polysquare-ci-scripts/branch/master)|[![Coverage](https://coveralls.io/repos/polysquare/polysquare-ci-scripts/badge.png?branch=master)](https://coveralls.io/r/polysquare/polysquare-ci-scripts?branch=master)|

## Usage ##

The idea behind these scripts is that their output is intended to be evaluated
by the parent shell. The main work is done inside the script itself (eg, in
python) and then we rely on the parent shell to save environment variables
and other state between script steps.

What these scripts do is set up a "container" with installations of
various programming languages or libraries in a self-contained manner. They
can be re-used across builds by adding the specified container to
the `cache` key of your `/.travis.yml` file.

`/bootstrap.py` is responsible for creating or re-using a container
and then executing a script which makes use of that container in some
fashion.

    Bootstrap CI Scripts

    optional arguments:
      -h, --help            show this help message and exit
      -d DIRECTORY, --directory DIRECTORY
                            Directory to store language runtimes, scripts and
                            other script details in
      -s SCRIPT, --script SCRIPT
                            Script to pass control to
      -e, --eval-output     Evaluate output
      -r SCRIPTS_DIRECTORY, --scripts-directory SCRIPTS_DIRECTORY
                            Directory where scripts are already stored in

The script passed to `--script` is expressed as a path relative to
the current directory, or, if such a file does not exist, then a path
relative to the `ciscripts` directory as hosted on
`http://public-travis-scripts.polysquare.org`. Scripts are downloaded
on-the-fly if they don't exist. This means that if you have a project using
a particular language that doesn't differ from the way most projects
using that language works, you can just refer to that language's setup
script and run it.

Scripts passed to `--script` must have a function named `run` defined as
follows:

    def run(container, util, parent_shell, **kwargs):

## Scripts and their functions ##

### Bootstrap script ###

This script passes control to other scripts. It also defines a function in
the parent shell called `polysquare_run` which provides a shorthand way
of calling itself in future.

### Setup scripts ###

Setup scripts are located at `/ciscripts/setup/language/setup.py` where language
indicates the language-type of the project which should be set up. The output
of a setup script should be evaluated as it will set environment variables in
the parent scope. Usually these environment variables will be set in order to
'activate' a certain language installation in the container.

Setup scripts ensure that a project's dependencies are installed.

### Check scripts ###

Check scripts are located at `/ciscripts/check/language/check.py` where
language indicates the language-type of the project which will be checked. This
step is responsible for running both static analysis, builds and any linters.
The output of these scripts does not need to be evaluated.

### Clean script ###

The clean script is located at `/ciscripts/clean.py` and is responsible for
cleaning out any set up language installations before the container directory
is compressed and uploaded for caching. Usually the various language
installations will register themselves in a text file upon installation and
this script will get a handle for their container and call its `clean` method.

The files cleaned are usually temporary files, source code, static libraries,
documentation and other files which are not necessary for installing any
additional programs or libraries in that language installation.

### Deploy script ###

Usually most languages will not provide this. However, in the case where
something from a language container is required for the deploy step, this
script can be evaluated and called from the bootstrap script in order to
set that thing up. It cannot be called with `polysquare_run` in the deploy
step as environment variables and functions are not defined at this point.

## Writing your own scripts ##

Generally speaking, scripts are designed to be called from other scripts and
`/bootstrap.py`. They should have a `run` function with the signature as
discussed earlier.

Scripts should never use any functionality that is not in the python
standard library, as there is no opportunity to install dependencies
safely with pip.

### The parent shell ###

Scripts should never print anything to the standard output, except by
using the `parent_shell` variable passed to them. The standard output is
evaluated by the parent shell, but the standard error is displayed on
screen.

The `parent_shell` variable defines the following functions:

- `overwrite_environment_variable`: Causes environment variable `key` to be
                                    overwritten with `value`.
- `remove_from_environment_variable`: Removes `value` from an environment
                                      variable list specified at `key`.
- `prepend_environment_variable`: Prepend `value` to environment variable list
                                  at `key`.
- `define_command`: Define a function which calls a specified command
                    with its arguments `key`.
- `exit`: Causes the shell to exit with a certain status.

Generally speaking you wouldn't use any of these functions directly, but you
would pass the `parent_shell` to an equivalent function on the `util` object,
which will also set environment variables in the current scope too.

### Dependencies ###

Dependencies between scripts must be expressed as passing modules around
as keyword arguments to the `run` function of those scripts. Fetch a module
using the `fetch_and_import` function on a container object. This will ensure
that the script is downloaded or re-used appropriately. Never express
dependencies as imports.

### The container object ###

The `ContainerDir` object is responsible for managing the "container" directory
specified on the command-line to `/bootstrap.py`. It manages three internal
directories:

- `_languages`: For all installations of programming languages which are not
                the language being used as the project language on travis-ci.
- `_scripts`: A local mirror of downloaded scripts.
- `_cache`: Both "named" and temporary cache directories.

The idea is that these directories are preserved between builds, to avoid
expensive re-installation of dependencies that we've already installed.

### Language directories ###

Any language directory expressed as a subclass of `LanguageBase` functions in
a similar way to the parent container directory. Language installations are
"activatable" in the sense that they all export the `activate`, `deactivate`,
`activated` and `deactivated` functions and context managers. These functions
set environment variables both in the local scope and parent scope to ensure
that dependencies are installed in to this language installation and that
any interpreters and compilers are launched from this language installation.

In order to implement a new type of language directory, you should subclass
the `LanguageBase` class. The main assumption is that any language
subclass will be created for a directory that already has that language
installed, so you will need to handle that yourself before creating the class.

Usually the subclass will implement the following functions:

- `clean`: This function is responsible for cleaning out the language directory
           such that it would be a suitable candidate for being cached. This
           means that all temporary files, documentation, build files and
           unneeded source code are removed.
- `_active_environment`: This function specifies the values that certain
                         environment variables will have when the language
                         installation is considered "active". It returns a
                         tuple as specified in its `tuple_type` argument with
                         the `overwrite` member set to a dictionary of
                         environment variables and their new values
                         (overwriting the old ones) and the `prepend` value
                         set to a dictionary of environment variables and
                         values to prepend to their existing value.

### Indicating which task is being run ###

Usually you wouldn't print anything to the standard error by yourself, but
instead use the `Task` API to specify when a task is being run. Tasks are
printed in a nested fashion. When task A is still running and task B starts,
it is considered a "sub-task" of task A and printed as indented within it.

In order to indicate that a certain task is running for a set of commands
use `Task` as a context manager, for example:

    with util.Task("Performing some action"):
        with util.Task("Performing sub-action one"):
            pass
        with util.Task("Performing sub-action two"):
            pass

### Executing commands ###

Some wrappers around the `subprocess` module are provided to execute certain
tasks and manage their output and return code.

The main function is the `execute` function in the `util` module. This
takes a `ContainerDir` and an output-management mode as its first two arguments,
with its remaining arguments being the arguments to pass to the command itself.

The output management modes are as follows:

- `util.output_on_fail`: Suppress all output unless there is an error, showing
                         it on the correct indent level.
- `util.running_output`: Show output by default, on the correct indent level.
- `util.long_running_suppressed_output(N)`: Like `util.output_on_fail` but
                                            prints dots every `N` seconds while
                                            the command is running. This ensures
                                            that for long running commands
                                            travis-ci will not time out waiting
                                            for additional output.

### Uniquely identifying a type of system ###

A system type identifier is useful for determining whether pre-compiled
binaries can be fetched from a certain location. This can be obtained
with the `get_system_identifier` function which is defined in the
`util` module.

### Functional programming constructs ###

The `util` module also provides some functions which simplify a number
of operations across files:

- `util.where_unavailable`: Runs `function` with `*args` and `**kwargs` where
                            `executable` is not found in the system's `PATH`.
- `util.apply_to_files`: Apply `func` to all files in `tree_node` which
                         match patterns in `matching` and do not match patterns
                         in `not_matching`, recursively.
- `util.apply_to_directories`: Apply `func` to all directories in `tree_node`
                         which match patterns in `matching` and do not match
                         patterns in `not_matching`, recursively.
