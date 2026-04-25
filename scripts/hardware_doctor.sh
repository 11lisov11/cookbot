#!/usr/bin/env bash
set -euo pipefail

python "$(dirname "$0")/hardware_tooling.py" hardware-doctor "$@"
