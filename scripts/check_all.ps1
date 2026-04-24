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
}
else {
    Write-Warning "arduino-cli not found; skipping firmware compile"
}

Write-Host "CookBot: all checks passed"

