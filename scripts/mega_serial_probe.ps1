$ErrorActionPreference = "Stop"
$tool = Join-Path $PSScriptRoot "hardware_tooling.py"
python $tool mega-serial-probe @args
