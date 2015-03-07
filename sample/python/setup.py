# /setup.py
#
# Installation and setup script for example python project
#
# See LICENCE.md for Copyright information
"""Installation and setup script for example python project."""

from setuptools import find_packages
from setuptools import setup

setup(name="example",
      version="0.0.1",
      description="Polysquare CI Scripts Example",
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
                   "License :: OSI Approved :: MIT License"],
      license="MIT",
      keywords="development linters",
      packages=find_packages(exclude=["tests"]),
      extras_require={
          "test": ["coverage",
                   "nose",
                   "nose-parameterized",
                   "testtools"]
      },
      test_suite="nose.collector",
      zip_safe=True,
      include_package_data=True)
