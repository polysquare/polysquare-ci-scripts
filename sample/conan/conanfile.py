from conans import ConanFile
from conans.tools import download, unzip
import os


class CMakeForwardArgumentsConan(ConanFile):
    name = "cmake-forward-cache"
    version = "master"
    generators = "cmake"
    requires = ("cmake-include-guard/master@smspillaz/cmake-include-guard", )
    url = "http://github.com/polysquare/cmake-forward-cache"
    license = "MIT"

    def source(self):
        zip_name = "cmake-forward-cache-master.zip"
        download("https://github.com/polysquare/" +
                 "cmake-forward-cache/archive/master.zip", zip_name)
        unzip(zip_name)
        os.unlink(zip_name)

    def package(self):
        self.copy(pattern="*.cmake",
                  dst="cmake/cmake-forward-cache",
                  src=".",
                  keep_path=True)
