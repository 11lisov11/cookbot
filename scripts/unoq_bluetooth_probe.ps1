$ErrorActionPreference = "Stop"
$tool = Join-Path $PSScriptRoot "hardware_tooling.py"
python $tool unoq-bluetooth-probe @args
