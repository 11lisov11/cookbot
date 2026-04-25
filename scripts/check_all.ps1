$ErrorActionPreference = "Stop"

Write-Host "CookBot: pytest"
python -m pytest tests/

Write-Host "CookBot: compileall"
python -m compileall unoq_backend

Write-Host "CookBot: backend smoke"
$env:COOKBOT_MODE = "simulator"
$env:COOKBOT_MEGA_TRANSPORT = "fake"
$env:COOKBOT_CAMERA = "mock"
$env:COOKBOT_AI = "mock"
$port = 8766
$backend = Start-Process -FilePath "python" -ArgumentList @("-m", "uvicorn", "unoq_backend.app:app", "--host", "127.0.0.1", "--port", "$port") -PassThru -WindowStyle Hidden
try {
    python scripts/smoke_backend.py "http://127.0.0.1:$port"
}
finally {
    if (!$backend.HasExited) {
        Stop-Process -Id $backend.Id -Force
    }
}

Write-Host "CookBot: fake Mega smoke"
python scripts/smoke_fake_mega.py

Write-Host "CookBot: web build"
Push-Location web
try {
    npm install
    npm run build
}
finally {
    Pop-Location
}

Write-Host "CookBot: Arduino Mega compile"
if (Get-Command arduino-cli -ErrorAction SilentlyContinue) {
    arduino-cli compile --fqbn arduino:avr:mega mega_firmware/cookbot_mega_firmware
    arduino-cli compile --fqbn arduino:avr:mega --build-property "build.extra_flags=-DCOOKBOT_BENCH_OUTPUTS_ENABLED=1" mega_firmware/cookbot_mega_firmware
}
else {
    Write-Warning "arduino-cli not found; skipping firmware compile"
}

Write-Host "CookBot: PlatformIO Mega build"
if (Get-Command pio -ErrorAction SilentlyContinue) {
    pio run -e cookbot_mega2560
    pio run -e cookbot_mega2560_bench
}
else {
    python -c "import platformio" 2>$null
    if ($LASTEXITCODE -eq 0) {
        python -m platformio run -e cookbot_mega2560
        python -m platformio run -e cookbot_mega2560_bench
    }
    else {
        Write-Warning "PlatformIO pio not found; skipping PlatformIO compile"
    }
}

Write-Host "CookBot: hardware automation dry-runs"
python scripts/hardware_tooling.py hardware-doctor --dry-run --json
python scripts/hardware_tooling.py unoq-adb-deploy --dry-run
python scripts/hardware_tooling.py unoq-adb-logs --dry-run
python scripts/hardware_tooling.py mega-platformio-upload --dry-run --port DRY_RUN_PORT
python scripts/hardware_tooling.py mega-serial-probe --dry-run --port DRY_RUN_PORT
python scripts/hardware_tooling.py commissioning-check --dry-run

Write-Host "CookBot: release bundle"
python scripts/release_tooling.py build --output dist/release --json
python scripts/release_tooling.py validate --latest --output dist/release --json

Write-Host "CookBot: all checks passed"
