$ErrorActionPreference = "Stop"

$tool = Join-Path $PSScriptRoot "release_tooling.py"
python $tool build @args
