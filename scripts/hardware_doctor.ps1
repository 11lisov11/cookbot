$ErrorActionPreference = "Stop"

$tool = Join-Path $PSScriptRoot "hardware_tooling.py"
python $tool hardware-doctor @args
