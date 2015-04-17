# /ciscripts/check/project/lint.py
#
# Check files in project for style guide compliance.
#
# See /LICENCE.md for Copyright information
"""Check files in project for style guide compliance."""

import os


def run(cont,  # suppress(too-many-arguments)
        util,
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
    technical_terms_path = os.path.join(cont.named_cache_dir("tech_terms"),
                                        "technical_terms.txt")

    extensions = extensions or list()
    exclusions = exclusions or list()
    directories = directories or [os.getcwd()]
    block_regexps = block_regexps or list()

    def lint(linter, *args):
        """Return a function which applies linter to a file."""
        def linter_function(file_to_lint):
            """Apply linter to file_to_lint."""
            util.execute(cont,
                         util.output_on_fail,
                         linter,
                         file_to_lint,
                         *args)

        return linter_function

    with util.Task("Linting files using polysquare style guide linter"):
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

            util.apply_to_files(lint("polysquare-generic-file-linter",
                                     "--spellcheck-cache",
                                     cache_dir,
                                     "--log-technical-terms-to",
                                     technical_terms_path,
                                     "--block-regexps",
                                     *block_regexps),
                                directory,
                                matching,
                                not_matching)

    with util.Task("Linting markdown documentation"):
        for directory in [os.path.realpath(d) for d in directories]:
            matching = ["*.md"]
            not_matching = ([e for e in exclusions] +
                            [os.path.join(cont.path(), "*")])

            util.apply_to_files(lint("mdl"),
                                directory,
                                matching,
                                not_matching)

            cache_dir = cont.named_cache_dir("markdown_spelling_cache")
            util.apply_to_files(lint("spellcheck-linter",
                                     "--spellcheck-cache",
                                     cache_dir,
                                     "--technical-terms",
                                     technical_terms_path),
                                directory,
                                matching,
                                not_matching)