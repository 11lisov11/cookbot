from pathlib import Path


def test_schema_endpoint_exposes_core_contracts(client):
    response = client.get("/schemas")
    assert response.status_code == 200
    body = response.json()
    assert "SystemState" in body
    assert "MegaRequest" in body
    assert "AIPlan" in body
    assert "HardwareReadinessResponse" in body
    assert "HardwareGateReport" in body
    assert "AcceptanceReport" in body
    assert "ExportBundle" in body
    assert "BackupBundle" in body
    assert "RestoreValidationResponse" in body
    assert "ProductReadinessResponse" in body
    assert "CommissioningGuideResponse" in body
    assert "VersionResponse" in body
    assert "VendorGCodeRequest" in body
    assert "VendorGCodeValidationResponse" in body
    assert "VendorProfileResponse" in body
    assert "StepperMotionEstimateRequest" in body
    assert "StepperMotionEstimateResponse" in body
    assert "CoordinateCalibrationRequest" in body
    assert "CoordinateCalibrationResponse" in body
    assert "ErrorTaxonomy" in body
    assert "invalid_motion_profile" in body["ErrorTaxonomy"]["config_error"]
    assert "MegaProtocolCommands" in body
    assert "bench_test_output" in body["MegaProtocolCommands"]
    assert "jog_axis" in body["MegaProtocolCommands"]
    assert "move_axis" in body["MegaProtocolCommands"]
    assert "seek_limit" in body["MegaProtocolCommands"]
    assert "get_motion_profile" in body["MegaProtocolCommands"]


def test_hardware_protocol_and_automation_docs_exist():
    assert Path("docs/mega_protocol.md").exists()
    assert Path("docs/hardware_automation.md").exists()
    assert Path("docs/commissioning_runbook.md").exists()
    assert Path("docs/bluetooth_link.md").exists()
    assert Path("docs/smart_home_integration.md").exists()
    assert Path("docs/vendor_axis4ui_protocol.md").exists()
    assert Path("deploy/homeassistant/cookbot_package.yaml").exists()
    assert Path("docs/release_bundle.md").exists()
    assert Path("platformio.ini").exists()
    assert Path(".vscode/tasks.json").exists()
    assert Path("scripts/hardware_doctor.ps1").exists()
    assert Path("scripts/hardware_doctor.sh").exists()
    assert Path("scripts/mega_ramps14_jog.ps1").exists()
    assert Path("scripts/mega_ramps14_jog.sh").exists()
    assert Path("docs/speed_tuning.md").exists()
    assert Path("scripts/build_release.ps1").exists()
    assert Path("scripts/validate_release.ps1").exists()


def test_windows_acceptance_script_checks_native_exit_codes():
    script = Path("scripts/check_all.ps1").read_text(encoding="utf-8")

    assert "function Invoke-Checked" in script
    assert 'Invoke-Checked "pytest"' in script
    assert 'Invoke-Checked "web build"' in script
    assert 'Invoke-Checked "Arduino RAMPS Bluetooth firmware compile"' in script
    assert 'Invoke-Checked "release bundle validation"' in script
