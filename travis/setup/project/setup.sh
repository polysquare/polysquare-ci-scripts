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

polysquare_fetch_and_fwd "setup/project/python_setup.sh" \
    -d "${CONTAINER_DIR}" \
    -v 2.7

polysquare_fetch_and_fwd "setup/project/ruby_setup.sh" \
    -d "${CONTAINER_DIR}" \
    -v 1.9.3-p551

polysquare_fetch_and_exec "setup/project/project.sh"
