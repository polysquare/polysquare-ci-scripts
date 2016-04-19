# /test/test_bootstrap.py
#
# Test cases for the bootstrap script.
#
# See /LICENCE.md for Copyright information
"""Test cases for the bootstrap script."""

import errno

import os

import shutil

import subprocess

import sys

import tempfile

from contextlib import contextmanager

# We depend on the implicit setting of
# util._NO_TASK_CACHING as a side-effect
# of importing this module.
from test import testutil

import ciscripts.bootstrap as bootstrap
import ciscripts.util as util

from nose_parameterized import param, parameterized

from testtools import TestCase
from testtools.matchers import (Contains,
                                DirExists,
                                FileContains,
                                FileExists,
                                Not)


class TestForceMkDir(TestCase):
    """Test cases for forcing directories to be created."""

    def test_force_single_mkdir(self):
        """Test forcing creation of a single directory (normal case)."""
        with testutil.in_tempdir(os.getcwd(), "force_mkdir_test"):
            directory = bootstrap.force_mkdir("forced_mkdir")
            self.assertThat(directory, DirExists())

    def test_force_multiple_layered_mkdir(self):
        """Test forcing creation of multi-layer directory."""
        with testutil.in_tempdir(os.getcwd(), "force_mkdir_test"):
            bootstrap.force_mkdir("forced/mkdir")
            self.assertThat(os.path.join(os.getcwd(), "forced/mkdir"),
                            DirExists())

    def test_open_file_in_forced_mkdir(self):
        """Test creating and opening files inside forced multi-layer dirs."""
        with testutil.in_tempdir(os.getcwd(), "force_mkdir_test"):
            with bootstrap.open_and_force_mkdir("forced/mkdir/file", "w") as f:
                f.write("")

            self.assertThat(os.path.join(os.getcwd(), "forced/mkdir/file"),
                            FileExists())

    def test_open_file_in_forced_mkdir_write(self):
        """Test creating and writing to files inside multi-layer dirs."""
        with testutil.in_tempdir(os.getcwd(), "force_mkdir_test"):
            with bootstrap.open_and_force_mkdir("forced/mkdir/file", "w") as f:
                f.write("Contents")

            self.assertThat(os.path.join(os.getcwd(), "forced/mkdir/file"),
                            FileContains("Contents"))


def write_bootstrap_script_into_container(directory_name):
    """Write a bootstrap script into the container specified."""
    scripts_dir = os.path.join(directory_name, "_scripts", "ciscripts")
    bootstrap.force_mkdir(scripts_dir)
    shutil.copyfile(os.path.join(os.path.dirname(bootstrap.__file__),
                                 "bootstrap.py"),
                    os.path.join(scripts_dir, "bootstrap.py"))
    shutil.copyfile(os.path.join(os.path.dirname(util.__file__),
                                 "util.py"),
                    os.path.join(scripts_dir, "util.py"))


@contextmanager
def removable_container_dir(directory_name):
    """A contextmanager which deletes a container when the test is complete."""
    current_cwd = os.getcwd()
    printer = bootstrap.escaped_printer_with_character("\\")
    shell = bootstrap.BashParentEnvironment(printer)
    try:
        # Put a /bootstrap.py script in the container directory
        # so that we don't keep on trying to fetch it all the time
        write_bootstrap_script_into_container(directory_name)
        yield bootstrap.ContainerDir(shell,
                                     directory=directory_name,
                                     stale_check=None)
    finally:
        util.force_remove_tree(os.path.join(current_cwd, directory_name))


class TrackedLoadedModulesTestCase(TestCase):
    """Test case that tracks loaded modules and unloads them as appropriate."""

    def __init__(self, *args, **kwargs):
        """Initialize this test case and set internal variables."""
        super(TrackedLoadedModulesTestCase, self).__init__(*args, **kwargs)
        self._loaded_modules = []

    def setUp(self):  # suppress(N802)
        """Ensure that bootstrap and util __file__ is absolute."""
        super(TrackedLoadedModulesTestCase, self).setUp()
        self.patch(bootstrap, "__file__", os.path.abspath(bootstrap.__file__))
        self.patch(util, "__file__", os.path.abspath(util.__file__))

    def tearDown(self):  # suppress(N802)
        """Ensure that any loaded modules are removed."""
        for module in self._loaded_modules:
            del sys.modules[module]

        super(TrackedLoadedModulesTestCase, self).tearDown()

    def note_loaded_module_path(self,
                                container,
                                module,
                                domain="public-travis-scripts.polysquare.org"):
        """Keep a note that we loaded module."""
        self._loaded_modules.append(container.loaded_module_name(module,
                                                                 domain))

    def note_loaded_module(self, module):
        """Keep a note that we loaded module."""
        self._loaded_modules.append(module)


def make_loadable_module_path(abs_path, loadable, mode="w"):
    """Make path a loadable module path.

    This means that if :abs_path: were to be broken up into
    a dot-separated import path, each component could be imported
    because it had its own /__init__.py. :loadable: must be the
    component of the path which should be considered loadable
    from that point onward.
    """
    try:
        os.makedirs(os.path.dirname(abs_path))
    except OSError as error:
        if error.errno != errno.EEXIST:  # suppress(PYC90)
            raise error

    directory_tree = os.path.dirname(os.path.relpath(abs_path, loadable))
    directory_tree_components = directory_tree.split(os.path.sep)

    for i in range(1, len(directory_tree_components) + 1):
        path = os.path.join(loadable,
                            *directory_tree_components[0:i])
        with open(os.path.join(path, "__init__.py"), "w"):
            pass

    return open(abs_path, mode)


class TestContainerDir(TrackedLoadedModulesTestCase):
    """Test cases for the ContainerDir class, which encapsulates everything."""

    def test_container_dir_exists(self):
        """Test ContainerDir exists at specified directory."""
        with testutil.in_tempdir(os.getcwd(), "container_dir_test"):
            with removable_container_dir("container"):
                self.assertThat(os.path.join(os.getcwd(), "container"),
                                DirExists())

    @parameterized.expand(["_scripts", "_languages", "_cache"])
    def test_container_dir_has_subdir(self, subdir):
        """Test ContainerDir has subdir."""
        with testutil.in_tempdir(os.getcwd(), "container_dir_test"):
            with removable_container_dir("container"):
                self.assertThat(os.path.join(os.getcwd(),
                                             "container",
                                             subdir),
                                DirExists())

    @parameterized.expand(["toplevel.py", "nested/nested.py"])
    def test_import_existing_module_in_scripts(self, module):
        """Test importing as a module in _scripts/."""
        with testutil.in_tempdir(os.getcwd(), "container_dir_test"):
            with removable_container_dir("container") as container:
                loadable = os.path.join(os.getcwd(), "container", "_scripts")
                module_path = os.path.join(loadable,
                                           "ciscripts",
                                           module)
                with make_loadable_module_path(module_path, loadable) as f:
                    f.write("CONSTANT = 1")
                    f.flush()

                    # Now import the file and make use of it
                    imported_module = container.fetch_and_import(module)
                    self.note_loaded_module_path(container, module)
                    self.assertEqual(1, imported_module.CONSTANT)

    @parameterized.expand(["toplevel.py", "nested/nested.py"])
    def test_fetch_modules_and_import(self, module):
        """Test importing as a fetched module."""
        with testutil.in_tempdir(os.getcwd(), "container_dir_test"):
            with testutil.server_in_tempdir(os.getcwd(), "server") as server:
                module_path = os.path.join(server[0], module)
                with bootstrap.open_and_force_mkdir(module_path, "w") as mfile:
                    mfile.write("CONSTANT = 1")
                    mfile.flush()

                with removable_container_dir("container") as container:
                    # Now import the file and make use of it
                    domain = server[1]
                    imported_module = container.fetch_and_import(module,
                                                                 domain)
                    self.note_loaded_module_path(container, module, domain)
                    self.assertEqual(1, imported_module.CONSTANT)

    def test_create_named_cache_dir(self):
        """Created named cache directory exists."""
        with testutil.in_tempdir(os.getcwd(), "container_dir_test"):
            with removable_container_dir("container") as container:
                cache_dir = container.named_cache_dir("name")

                self.assertThat(cache_dir, DirExists())

    def test_create_language_dir(self):
        """Created language directory exists."""
        with testutil.in_tempdir(os.getcwd(), "container_dir_test"):
            with removable_container_dir("container") as container:
                language_dir = container.language_dir("name")

                self.assertThat(language_dir, DirExists())

    def test_named_cache_dir_is_subdir_of_cache_dir(self):
        """Created named cache directory is a subdir of container cache."""
        with testutil.in_tempdir(os.getcwd(),
                                 "container_dir_test") as temp_dir:
            with removable_container_dir("container") as container:
                cache_dir = container.named_cache_dir("name")
                self.assertEqual(os.path.join(temp_dir,
                                              "container",
                                              "_cache",
                                              "name"),
                                 cache_dir)

    def test_temp_cache_dir_is_subdir_of_cache_dir(self):
        """Created temporary cache directory is a subdir of container cache."""
        with testutil.in_tempdir(os.getcwd(),
                                 "container_dir_test") as temp_dir:
            with removable_container_dir("container") as container:
                with container.in_temp_cache_dir() as cache_dir:
                    self.assertEqual(os.path.join(temp_dir,
                                                  "container",
                                                  "_cache",
                                                  os.path.basename(cache_dir)),
                                     cache_dir)

    def test_named_language_dir_is_subdir_of_languages_dir(self):
        """Created language dir is a subdir of container languages dir."""
        with testutil.in_tempdir(os.getcwd(),
                                 "container_dir_test") as temp_dir:
            with removable_container_dir("container") as container:
                language_dir = container.language_dir("name")
                self.assertEqual(os.path.join(temp_dir,
                                              "container",
                                              "_languages",
                                              "name"),
                                 language_dir)


class TestBashParentEnvironment(TestCase):
    """Test cases for specific functionality in bash parent environment."""

    @parameterized.expand([param(x) for x in range(0, 10)])
    def test_print_exit_status_script(self, status):
        """Exit parent script with status."""
        evaluate_script = bytearray()

        def printer(script):
            """Add script to evaluate_script."""
            evaluate_script.extend(script.encode() + b";\n")

        environment = bootstrap.BashParentEnvironment(printer)
        environment.exit(status)
        process = subprocess.Popen(["bash", "-"],
                                   stdin=subprocess.PIPE)
        process.communicate(input=bytes(evaluate_script))
        process.stdin.close()
        self.assertEqual(process.wait(), status)


def _parent_env(output, key):
    """Get environment variable in shell after evaluating output."""
    result = subprocess.check_output(["bash",
                                      "-c",
                                      output +
                                      (" echo \"${%s}\"" % key)]).strip()
    return result.decode()


class TestLanguageContainer(TrackedLoadedModulesTestCase):
    """Test cases for the LanguageContainer abstract base class."""

    def __init__(self, *args, **kwargs):
        """Initialize this test case and set default variables."""
        super(TestLanguageContainer, self).__init__(*args, **kwargs)
        self._container = None
        self._util = None

    def setUp(self):  # suppress(N802)
        """Set up TestLanguageContainer.

        Load scripts/util.py and make a note of it.
        """
        super(TestLanguageContainer, self).setUp()
        container_dir = tempfile.mkdtemp(prefix="language_cont_test",
                                         dir=os.getcwd())
        self.addCleanup(util.force_remove_tree, container_dir)

        parent = os.path.realpath(os.path.join(os.path.dirname(__file__),
                                               ".."))
        assert "ciscripts" in os.listdir(parent)

        shutil.copytree(os.path.join(parent, "ciscripts"),
                        os.path.join(container_dir,
                                     "_scripts",
                                     "ciscripts"))

        printer = bootstrap.escaped_printer_with_character("\\")
        shell = bootstrap.BashParentEnvironment(printer)
        self._container = bootstrap.ContainerDir(shell,
                                                 directory=container_dir,
                                                 stale_check=None)
        self._util = self._container.fetch_and_import("util.py")
        self.note_loaded_module_path(self._container, "util.py")

    def _get_lang_container(self, language, override=None, prepend=None):
        """Get an empty implementation of LanguageBase."""
        container = self._container

        class EmptyLanguageContainer(container.new_container_for(language,
                                                                 "0.0")):
            """Concrete implementation of LanguageBase."""

            def __init__(self):
                """Initialize this EmptyLanguageContainer with language."""
                installation = container.language_dir(language)
                printer = bootstrap.escaped_printer_with_character("\\")
                shell = bootstrap.BashParentEnvironment(printer)
                super(EmptyLanguageContainer, self).__init__(installation,
                                                             language,
                                                             "0.0",
                                                             shell)

                self._override = override or dict()  # suppress(PYC70)
                self._prepend = prepend or dict()  # suppress(PYC70)

            def clean(self, util_mod):   # suppress(no-self-use)
                """Clean out this container."""
                del util_mod

            def _active_environment(self, tuple_type):
                """Get this language container's environment."""
                # suppress(PYC70)
                return tuple_type(self._override, self._prepend)

        return EmptyLanguageContainer()

    @contextmanager
    def activated_local_envion(self, *args, **kwargs):
        """Context with os.environ of an activated container."""
        language_container = self._get_lang_container(*args, **kwargs)

        with testutil.CapturedOutput():
            with language_container.activated(self._util):
                try:
                    yield os.environ
                finally:
                    pass

    @contextmanager
    def active_parent_env(self, *args, **kwargs):
        """Context with parent script of an activated container."""
        language_container = self._get_lang_container(*args, **kwargs)
        captured_output = testutil.CapturedOutput()

        with captured_output:
            language_container.activate(self._util)

        try:
            yield captured_output.stdout
        finally:
            with testutil.CapturedOutput():
                language_container.deactivate(self._util)

    def test_get_executable_path(self):
        """Get executable path from prepend variable."""
        prepend = {
            "PATH": "VALUE"
        }
        lang_container = self._get_lang_container("language",
                                                  prepend=prepend,
                                                  override=dict())

        self.assertEqual(lang_container.executable_path(),
                         "VALUE")

    def test_activating_container_returns_true(self):
        """Activating container returns true initially."""
        def cleanup():
            """Deactivate the container, don't emit output."""
            with testutil.CapturedOutput():
                language_container.deactivate(self._util)

        with testutil.CapturedOutput():
            language_container = self._get_lang_container("language")
            self.addCleanup(cleanup)
            self.assertTrue(language_container.activate(self._util))

    def test_deactivating_container_returns_true(self):
        """Deactivating activated container returns true initially."""
        with testutil.CapturedOutput():
            language_container = self._get_lang_container("language")
            with language_container.activated(self._util):
                self.assertTrue(language_container.deactivate(self._util))

    def test_double_activating_container_returns_false(self):
        """Activating container twice returns false on second try."""
        self.addCleanup(lambda: language_container.deactivate(self._util))
        with testutil.CapturedOutput():
            language_container = self._get_lang_container("language")
            with language_container.activated(self._util):
                self.assertFalse(language_container.activate(self._util))

    def test_double_deactivating_container_returns_false(self):
        """Deactivating container twice returns false on second try."""
        with testutil.CapturedOutput():
            language_container = self._get_lang_container("language")
            with language_container.activated(self._util):
                language_container.deactivate(self._util)
                self.assertFalse(language_container.deactivate(self._util))

    def test_activated_container_sets_language_verison_var(self):
        """Activating a container sets _POLYSQUARE_ACTIVATED_LANG_0_0."""
        with self.activated_local_envion("lang") as env:
            self.assertThat(env,
                            Contains("_POLYSQUARE_ACTIVATED_LANG_0_0"))

    def test_activated_container_sets_polysquare_active_env_var_parent(self):
        """Activating a container exports _POLYSQUARE_ACTIVATED_LANG_0_0."""
        with self.active_parent_env("lang") as out:
            env = "_POLYSQUARE_ACTIVATED_LANG_0_0"
            self.assertEqual(_parent_env(out, env),
                             "1")

    def test_activated_container_sets_overwritten_env_vars(self):
        """Activating a container overwrites environment variables locally."""
        override = {
            "VARIABLE": "VALUE"
        }

        with self.activated_local_envion("language", override=override) as env:
            self.assertEqual(env["VARIABLE"], "VALUE")

    def test_activated_container_sets_overwritten_env_vars_parent(self):
        """Activating a container overwrites variables in parent context."""
        override = {
            "VARIABLE": "VALUE"
        }

        with self.active_parent_env("language", override=override) as out:
            self.assertEqual(_parent_env(out, "VARIABLE"),
                             "VALUE")

    def test_activated_container_prepends_env_vars(self):
        """Activating a container prepends environment variables locally."""
        prepend = {
            "PATH": "VALUE"
        }

        with self.activated_local_envion("language", prepend=prepend) as env:
            self.assertThat(env["PATH"].split(os.pathsep),
                            Contains("VALUE"))

    def test_activated_container_prepends_env_vars_parent(self):
        """Activating a container prepends variables in parent context."""
        prepend = {
            "PATH": "VALUE"
        }

        with self.active_parent_env("language", prepend=prepend) as out:
            self.assertThat(_parent_env(out, "PATH").split(":"),
                            Contains("VALUE"))

    def test_overwritten_env_vars_restored_on_deactivate(self):
        """Overwritten environment variables restored on deactivate locally."""
        os.environ["VARIABLE"] = "OLD_VALUE"
        self.addCleanup(lambda: os.environ.__delitem__("VARIABLE"))

        with testutil.CapturedOutput():
            language_container = self._get_lang_container("language",
                                                          override={
                                                              "PATH": "VALUE"
                                                          })
            with language_container.activated(self._util):
                pass

        self.assertEqual(os.environ["VARIABLE"], "OLD_VALUE")

    def test_overwritten_env_vars_restored_on_deactivate_parent(self):
        """Overwritten environment vars restored in parent on deactivate."""
        os.environ["VARIABLE"] = "OLD_VALUE"
        self.addCleanup(lambda: os.environ.__delitem__("VARIABLE"))

        captured_output = testutil.CapturedOutput()

        with captured_output:
            language_container = self._get_lang_container("language",
                                                          override={
                                                              "PATH": "VALUE"
                                                          })
            with language_container.activated(self._util):
                pass

        out = "export VARIABLE=\"OLD_VALUE\";\n" + captured_output.stdout
        self.assertEqual(_parent_env(out, "VARIABLE"),
                         "OLD_VALUE")

    def test_prepended_env_vars_removed_on_deactivate(self):
        """Prepended environment vars are removed from parent on deactivate."""
        with testutil.CapturedOutput():
            language_container = self._get_lang_container("language",
                                                          prepend={
                                                              "PATH": "VALUE"
                                                          })
            with language_container.activated(self._util):
                pass

        self.assertThat(os.environ["PATH"].split(os.pathsep),
                        Not(Contains("VALUE")))

    def test_prepended_env_vars_removed_on_deactivate_in_parent(self):
        """Prepended environment vars are removed from parent on deactivate."""
        captured_output = testutil.CapturedOutput()

        with captured_output:
            language_container = self._get_lang_container("language",
                                                          prepend={
                                                              "PATH": "VALUE"
                                                          })
            with language_container.activated(self._util):
                pass

        self.assertThat(_parent_env(captured_output.stdout,
                                    "PATH").split(os.pathsep),
                        Not(Contains("VALUE")))


def _write_setup_script(script_contents):
    """Write script_contents to setup script and return its path."""
    loadable = os.path.abspath("container/_scripts")
    setup_script_path = os.path.abspath(os.path.join(loadable,
                                                     "ciscripts",
                                                     "setup",
                                                     "test",
                                                     "setup.py"))
    with make_loadable_module_path(setup_script_path, loadable) as f:
        # Write a simple script to our setup file
        f.write(script_contents)

    return "setup/test/setup.py"


class TestMain(TrackedLoadedModulesTestCase):
    """Test cases for creating containers on the command line."""

    def __init__(self, *args, **kwargs):
        """Initialize instance variables on this TestCase."""
        super(TestMain, self).__init__(*args, **kwargs)
        self._test_dir = None
        self._container_dir = None

    def setUp(self):  # suppress(N802)
        """Set up TestMain.

        Create a temporary directory to perform all actions in.
        """
        super(TestMain, self).setUp()
        current_dir = os.getcwd()
        prefix = os.path.join(current_dir, "main_container_test")
        self._test_dir = tempfile.mkdtemp(prefix=prefix)
        self.addCleanup(util.force_remove_tree, self._test_dir)
        self._container_dir = os.path.join(self._test_dir, "container")
        os.chdir(self._test_dir)
        self.addCleanup(os.chdir, current_dir)

        write_bootstrap_script_into_container(self._container_dir)

    def test_create_dir_and_pass_control_to_script(self):
        """Test creating a container and passing control to a script."""
        _write_setup_script("def run(cont, util, sh, argv):\n"
                            "    print(\"Hello\")\n")

        captured_output = testutil.CapturedOutput()

        with captured_output:
            bootstrap.main(["-d",
                            self._container_dir,
                            "-s",
                            "setup/test/setup.py",
                            "--keep-scripts"])

        self.assertEqual(captured_output.stdout, "Hello\n\n")

    def test_create_dir_and_pass_args_to_script(self):
        """Test creating a container and passing arguments to a script."""
        _write_setup_script("def run(cont, util, sh, argv):\n"
                            "    print(argv[0])\n")

        captured_output = testutil.CapturedOutput()

        with captured_output:
            bootstrap.main(["-d",
                            self._container_dir,
                            "-s",
                            "setup/test/setup.py",
                            "--keep-scripts",
                            "Argument"])

        self.assertEqual(captured_output.stdout, "Argument\n\n")

    def test_create_dir_and_pass_control_to_downloaded_script(self):
        """Test creating container and passing control to a fetched script."""
        with testutil.server_in_tempdir(os.getcwd(), "server") as server:
            util_script = os.path.join(server[0], "util.py")
            with bootstrap.open_and_force_mkdir(util_script, "w") as f:
                f.write("")
                f.flush()

            setup_script = os.path.join(server[0], "setup/test/setup.py")
            with bootstrap.open_and_force_mkdir(setup_script, "w") as f:
                # Write a simple script to our setup file
                f.write("def run(cont, util, sh, argv):\n"
                        "  print(\"Hello\")\n")
                f.flush()

                dns_overrides = {
                    "public-travis-scripts.polysquare.org": server[1]
                }

            with testutil.overridden_dns(dns_overrides):
                with testutil.in_tempdir(os.getcwd(), "container"):
                    captured_output = testutil.CapturedOutput()

                    with captured_output:
                        bootstrap.main(["-d",
                                        self._container_dir,
                                        "-s",
                                        "setup/test/setup.py",
                                        "--keep-scripts"])

                    self.assertEqual(captured_output.stdout, "Hello\n\n")
