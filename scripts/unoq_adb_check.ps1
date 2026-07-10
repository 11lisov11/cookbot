$ErrorActionPreference = "Stop"
$tool = Join-Path $PSScriptRoot "hardware_tooling.py"
python $tool unoq-adb-check @args
