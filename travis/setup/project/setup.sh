#!/usr/bin/env bash
# /travis/setup/project/setup.sh
#
# Travis CI Script which just sets up project style guide and markdown
# documentation checkers. It does not set up anything else. For a specific
# langauge, consider using that setup/language/setup.sh instead.
#
#     eval $(curl -LSs path/to/setup.sh | bash)
#
# See LICENCE.md for Copyright information

source "${POLYSQUARE_CI_SCRIPTS_DIR}/util.sh"

polysquare_fetch_and_fwd "setup/project/language.sh" \
    -l python \
    -l ruby \
    -d "${CONTAINER_DIR}"
polysquare_fetch_and_exec "setup/project/project.sh"
