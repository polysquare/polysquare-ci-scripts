from contextlib import contextmanager

import os

from conans import ConanFile, CMake


@contextmanager
def in_dir(directory):
    last_dir = os.getcwd()
    try:
        os.makedirs(directory)
    except OSError:
        pass

    try:
        os.chdir(directory)
        yield directory
    finally:
        os.chdir(last_dir)


class CPPProjectConan(ConanFile):
    """Conan project for sample polysquare project."""

    name = "cpp-project"
    version = "master"
    generators = "cmake"
    requires = tuple()
    url = "http://github.com/polysquare/cpp-project"
    license = "MIT"

    def build(self):
        """Build conan project."""
        cmake = CMake(self.settings)
        with in_dir("build"):
            self.run("cmake '{src}' {cmd}".format(src=self.conanfile_directory,
                                                  cmd=cmake.command_line))
            self.run("cmake --build . {cfg}".format(cmake.build_config))
