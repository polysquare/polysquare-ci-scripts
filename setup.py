# /setup.py
#
# Installation and setup script for polysquare-ci-scripts
#
# See /LICENCE.md for Copyright information
"""Installation and setup script for polysquare-ci-scripts."""

from setuptools import (find_packages, setup)

setup(name="polysquare-ci-scripts",
      version="0.0.1",
      description="Polysquare Continuous Integration Scripts",
      long_description_markdown_filename="README.md",
      author="Sam Spilsbury",
      author_email="smspillaz@gmail.com",
      url="http://github.com/polysquare/polysquare-ci-scripts",
      classifiers=["Development Status :: 3 - Alpha",
                   "Programming Language :: Python :: 2",
                   "Programming Language :: Python :: 2.7",
                   "Programming Language :: Python :: 3",
                   "Programming Language :: Python :: 3.1",
                   "Programming Language :: Python :: 3.2",
                   "Programming Language :: Python :: 3.3",
                   "Programming Language :: Python :: 3.4",
                   "Intended Audience :: Developers",
                   "Topic :: Software Development :: Build Tools",
                   "License :: OSI Approved :: MIT License"],
      license="MIT",
      keywords="development linters",
      packages=find_packages(exclude=["test"]),
      extras_require={
          "green": [
              "nose",
              "nose-parameterized>=0.4.0",
              "mock",
              "setuptools-green",
              "six",
              "testtools"
          ],
          "polysquarelint": ["polysquare-setuptools-lint"],
          "upload": ["setuptools-markdown>=0.1"]
      },
      zip_safe=True,
      include_package_data=True)
