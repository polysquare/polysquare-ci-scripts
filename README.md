# Polysquare CI Scripts #

Polysquare CI Scripts (common to a few modules).

A redirect to the raw version of these scripts exists at
`public-travis-scripts.polysquare.org`. You can `wget` them by script name
in your `travis.yml` like so:

    - wget public-travis-scripts.polysquare.org/python-install.sh
    - bash python-install.sh

## Status ##

| Travis CI (Ubuntu) |
|--------------------|
|[![Travis](https://travis-ci.org/polysquare/polysquare-ci-scripts.svg?branch=master)](https://travis-ci.org/polysquare/polysquare-ci-scripts)

## Usage ##

The following scripts perform the following functions

### For all project types ###

#### `distro-container.sh` ####

Wraps `polysquare-travis-container-create` to create a new container for
a Linux distribution as specified by the environment variables
`CONTAINER_DISTRO`, `CONTAINER_RELEASE` and `CONTAINER_ARCH`. If the files
`DEPENDENCIES.{Distro}` and `REPOSITORIES.{Distro}` then they will be read
for package and repository names respectively and installed as part of
the distribution.

Use `-p` to specify the path in which the distribution rootfs should be
set up. It is advisable to cache this directory using the following
in your .travis.yml

    cache:
      directories:
        - {path}

If you need to make changes to the distribution, then the correct way to
do so is to upload the new travis.yml, DEPENDENCIES and REPOSITORIES files
and delete the build cache on Travis-CI

#### `setup-lang.sh` ####

Sets up local installations of various programming languages so that their
dependencies can be managed locally without having to touch the root
file-system.

Use `-p` to specify where the local installation prefix should be. This
directory should be cached.

Use `-l` for each language that you need to set up. Valid languages are:

* `python`
* `haskell`
* `ruby`

#### `prepare-lang-cache.sh` ####

Use at the end of the build-process to copy all installed packages for
set up langauges to the central build cache directory as specified by
`-p`.

Use `-l` to specify each language for which installed packages should
be cached.

#### `project-lint.sh` ####

Lints every file in the project for the Polysquare style guide and Markdown
style guide using Markdownlint and `polysquare-generic-file-linter`.

* Use `-d` for each directory to apply linting to.
* Use `-e` for each file extension to consider as part of the style guide. The
  default is to check every file in each directory, recursively, which is
  probably not the desired behaviour.
* Use `-x` to specify a list of filenames to exclude.

### Python specific ####

#### `python-install.sh` ####

Installs the python project and its dependencies, including any dependencies
specified under `extra_requires` for `test` in `setup.py`

#### `python-lint.sh` ####

Lints the python module specified by `-m` as well as a directory called
`tests` and `setup.py` comprehensively, using the following linters:

* `prospector`
* `pylint`
* `dodgy`
* `frosted`
* `mccabe`
* `pep257`
* `pep8`
* `pyflakes`
* `pyroma`
* `pychecker`
* `flake8` (with `blind-except`, `docstrings`, `double-quotes`, `import-order`
  and `todo` plugins)

#### `python-tests.sh` ####

Runs tests for module specified by `-m` and collects coverage information only
for that module.

#### `python-coverage.sh` ####

Reports collected coverage and uploads to coveralls.

### Shell specific ###

#### `shell-lint.sh` ####

Runs `shellcheck` and `bashlint` on each file in the directories specified by
`-d` (excluding any files specified by `-x`). All warnings are fatal.
