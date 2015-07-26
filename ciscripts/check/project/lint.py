# /ciscripts/check/project/lint.py
#
# Check files in project for style guide compliance.
#
# See /LICENCE.md for Copyright information
"""Check files in project for style guide compliance."""

import os


def run(cont,  # suppress(too-many-arguments)
        util,
        shell,
        argv,
        no_mdl=False,
        extensions=None,
        directories=None,
        exclusions=None,
        block_regexps=None):
    """Run the style guide linters on this project.

    By default, polysquare-generic-file-linter will not be run on anything. To
    run it on some files, specify some file extensions to check with
    :extensions:.

    All linters will run recursively from the project directory down. To only
    lint certain directories, specify :directories: in the keyword arguments.

    To exclude certain files, pass the absolute path to those files in
    :exclusions:.

    To exclude certain expressions from being considered by the spellchecker,
    pass them to :block_regexps:
    """
    del shell
    del argv

    technical_terms_path = os.path.join(cont.named_cache_dir("tech_terms",
                                                             ephemeral=False),
                                        "technical_terms.txt")

    extensions = extensions or list()
    exclusions = exclusions or list()
    directories = directories or [os.getcwd()]
    block_regexps = block_regexps or list()

    def lint(linter, *args):
        """Run linter with args."""
        util.execute(cont,
                     util.output_on_fail,
                     linter,
                     *args)

    def run_linters_on_code_files(extensions,
                                  exclusions,
                                  directories,
                                  block_regexps):
        """Run polysquare-generic-file-linter on code files."""
        for directory in [os.path.realpath(d) for d in directories]:
            matching = ["*.{0}".format(e) for e in extensions]
            not_matching = ([e for e in exclusions] +
                            [os.path.join(cont.path(), "*"),
                             os.path.join(os.getcwd(), ".eggs", "*"),
                             os.path.join(os.getcwd(), "*.egg", "*")])

            cache_dir = cont.named_cache_dir("code_spelling_cache")
            block_regexps = block_regexps + [
                r"\bsuppress\([^\s]*\)"
            ]

            files_to_lint = util.apply_to_files(lambda x: x,
                                                directory,
                                                matching,
                                                not_matching)

            if len(files_to_lint):
                lint("polysquare-generic-file-linter",
                     *(files_to_lint +
                       ["--spellcheck-cache",
                        cache_dir,
                        "--log-technical-terms-to",
                        technical_terms_path,
                        "--stamp-file-path",
                        cont.named_cache_dir("generic_linter",
                                             ephemeral=False),
                        "--block-regexps"] +
                       block_regexps))

    def run_linters_on_markdown_files(exclusions,
                                      directories,
                                      no_mdl):
        """Run spellcheck-linter and markdownlint on markdown files."""
        for directory in [os.path.realpath(d) for d in directories]:
            matching = ["*.md"]
            not_matching = ([e for e in exclusions] +
                            [os.path.join(cont.path(), "*")])

            cache_dir = cont.named_cache_dir("markdown_spelling_cache")
            files_to_lint = util.apply_to_files(lambda p: p,
                                                directory,
                                                matching,
                                                not_matching)

            if len(files_to_lint) > 0:
                lint("spellcheck-linter",
                     *(files_to_lint +
                       ["--spellcheck-cache",
                        cache_dir,
                        "--technical-terms",
                        technical_terms_path,
                        "--stamp-file-path",
                        cont.named_cache_dir("generic_linter",
                                             ephemeral=False)]))

                if not no_mdl:
                    for markdown_file in files_to_lint:
                        lint("mdl", markdown_file)

    with util.Task("""Linting files using polysquare style guide linter"""):
        run_linters_on_code_files(extensions,
                                  exclusions,
                                  directories,
                                  block_regexps)

    with util.Task("""Linting markdown documentation"""):
        run_linters_on_markdown_files(extensions,
                                      directories,
                                      no_mdl)
