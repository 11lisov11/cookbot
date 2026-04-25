#!/usr/bin/env bash
set -euo pipefail

python "$(dirname "$0")/release_tooling.py" validate "$@"
