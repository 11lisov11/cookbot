$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

Write-Host "CookBot: pytest"
Invoke-Checked "pytest" { python -m pytest tests/ }

Write-Host "CookBot: compileall"
Invoke-Checked "compileall" { python -m compileall unoq_backend }

Write-Host "CookBot: backend smoke"
$env:COOKBOT_MODE = "simulator"
$env:COOKBOT_MEGA_TRANSPORT = "fake"
$env:COOKBOT_CAMERA = "mock"
$env:COOKBOT_AI = "mock"
$port = 8766
$backend = Start-Process -FilePath "python" -ArgumentList @("-m", "uvicorn", "unoq_backend.app:app", "--host", "127.0.0.1", "--port", "$port") -PassThru -WindowStyle Hidden
try {
    Invoke-Checked "backend smoke" { python scripts/smoke_backend.py "http://127.0.0.1:$port" }
}
finally {
    if (!$backend.HasExited) {
        Stop-Process -Id $backend.Id -Force
    }
}

Write-Host "CookBot: fake Mega smoke"
Invoke-Checked "fake Mega smoke" { python scripts/smoke_fake_mega.py }

Write-Host "CookBot: web build"
Push-Location web
try {
    Invoke-Checked "npm install" { npm install }
    Invoke-Checked "web build" { npm run build }
}
finally {
    Pop-Location
}

Write-Host "CookBot: Arduino Mega compile"
if (Get-Command arduino-cli -ErrorAction SilentlyContinue) {
    Invoke-Checked "Arduino locked firmware compile" { arduino-cli compile --fqbn arduino:avr:mega mega_firmware/cookbot_mega_firmware }
    Invoke-Checked "Arduino bench firmware compile" { arduino-cli compile --fqbn arduino:avr:mega --build-property "build.extra_flags=-DCOOKBOT_BENCH_OUTPUTS_ENABLED=1" mega_firmware/cookbot_mega_firmware }
    Invoke-Checked "Arduino RAMPS Bluetooth firmware compile" { arduino-cli compile --fqbn arduino:avr:mega --build-property "build.extra_flags=-DCOOKBOT_HARDWARE_CONFIGURED=1 -DCOOKBOT_RAMPS14_COMMISSIONING=1 -DCOOKBOT_BLUETOOTH_UART_ENABLED=1 -DCOOKBOT_BLUETOOTH_UART_PORT=2 -DCOOKBOT_BLUETOOTH_BAUD=9600UL" mega_firmware/cookbot_mega_firmware }
}
else {
    Write-Warning "arduino-cli not found; skipping firmware compile"
}

Write-Host "CookBot: PlatformIO Mega build"
if (Get-Command pio -ErrorAction SilentlyContinue) {
    Invoke-Checked "PlatformIO locked firmware build" { pio run -e cookbot_mega2560 }
    Invoke-Checked "PlatformIO bench firmware build" { pio run -e cookbot_mega2560_bench }
    Invoke-Checked "PlatformIO RAMPS Bluetooth firmware build" { pio run -e cookbot_mega2560_ramps14_bluetooth }
}
else {
    python -c "import platformio" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Invoke-Checked "PlatformIO locked firmware build" { python -m platformio run -e cookbot_mega2560 }
        Invoke-Checked "PlatformIO bench firmware build" { python -m platformio run -e cookbot_mega2560_bench }
        Invoke-Checked "PlatformIO RAMPS Bluetooth firmware build" { python -m platformio run -e cookbot_mega2560_ramps14_bluetooth }
    }
    else {
        Write-Warning "PlatformIO pio not found; skipping PlatformIO compile"
    }
}

Write-Host "CookBot: hardware automation dry-runs"
Invoke-Checked "hardware doctor dry-run" { python scripts/hardware_tooling.py hardware-doctor --dry-run --json }
Invoke-Checked "UNO Q ADB deploy dry-run" { python scripts/hardware_tooling.py unoq-adb-deploy --dry-run }
Invoke-Checked "UNO Q ADB logs dry-run" { python scripts/hardware_tooling.py unoq-adb-logs --dry-run }
Invoke-Checked "UNO Q Bluetooth check dry-run" { python scripts/hardware_tooling.py unoq-bluetooth-check --dry-run --json }
Invoke-Checked "UNO Q Bluetooth pair dry-run" { python scripts/hardware_tooling.py unoq-bluetooth-pair --address AA:BB:CC:DD:EE:FF --dry-run }
Invoke-Checked "UNO Q Bluetooth probe dry-run" { python scripts/hardware_tooling.py unoq-bluetooth-probe --address AA:BB:CC:DD:EE:FF --dry-run }
$gitBash = @(
    "C:\Program Files\Git\bin\bash.exe",
    "C:\Program Files\Git\usr\bin\bash.exe"
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($gitBash) {
    & $gitBash -n scripts/unoq_bluetooth_capabilities.sh
    if ($LASTEXITCODE -ne 0) { throw "unoq_bluetooth_capabilities.sh syntax check failed" }
}
else {
    Write-Warning "Git Bash not found; shell syntax is checked by Linux CI"
}
Invoke-Checked "Mega upload dry-run" { python scripts/hardware_tooling.py mega-platformio-upload --dry-run --port DRY_RUN_PORT }
Invoke-Checked "Mega serial probe dry-run" { python scripts/hardware_tooling.py mega-serial-probe --dry-run --port DRY_RUN_PORT }
Invoke-Checked "commissioning dry-run" { python scripts/hardware_tooling.py commissioning-check --dry-run }

Write-Host "CookBot: release bundle"
Invoke-Checked "release bundle build" { python scripts/release_tooling.py build --output dist/release --json }
Invoke-Checked "release bundle validation" { python scripts/release_tooling.py validate --latest --output dist/release --json }

Write-Host "CookBot: all checks passed"
