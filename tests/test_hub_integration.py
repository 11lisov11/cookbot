from pathlib import Path

import yaml

from unoq_backend import __version__


ROOT = Path(__file__).resolve().parents[1]


class HomeAssistantLoader(yaml.SafeLoader):
    pass


HomeAssistantLoader.add_constructor(
    "!secret", lambda loader, node: {"secret": loader.construct_scalar(node)}
)


def test_release_versions_are_synchronized():
    package = yaml.safe_load((ROOT / "config/vendor_controller_profile.yaml").read_text())
    web_package = yaml.safe_load((ROOT / "web/package.json").read_text())

    assert __version__ == "0.3.0"
    assert web_package["version"] == __version__
    assert package["project"] == "CookBot"


def test_vendor_profile_records_evidenced_protocol_without_enabling_gcode():
    profile = yaml.safe_load(
        (ROOT / "config/vendor_controller_profile.yaml").read_text(encoding="utf-8")
    )
    commissioning = yaml.safe_load(
        (ROOT / "config/axis_commissioning.yaml").read_text(encoding="utf-8")
    )

    assert profile["transport"]["android_bluetooth_profile"] == "bluetooth_classic_spp_rfcomm"
    assert profile["transport"]["android_spp_uuid"] == "00001101-0000-1000-8000-00805f9b34fb"
    assert profile["motion"]["coordinate_axes"] == ["X", "Y", "Z", "E"]
    assert profile["safety"]["direct_vendor_gcode_enabled"] is False
    assert commissioning["controller_transport"]["bluetooth_uart"] == "Serial2"
    assert commissioning["axes"]["E0"]["limit_pin"] is None
    assert commissioning["axes"]["B"]["status"].startswith("inconsistent")


def test_home_assistant_package_is_restricted_to_state_and_estop():
    package_path = ROOT / "deploy/homeassistant/cookbot_package.yaml"
    package = yaml.load(package_path.read_text(encoding="utf-8"), Loader=HomeAssistantLoader)

    assert {"rest", "template", "rest_command", "script"} <= package.keys()
    assert set(package["rest_command"]) == {"cookbot_estop"}
    assert package["rest_command"]["cookbot_estop"]["url"].endswith("/estop")
    assert set(package["script"]) == {"cookbot_emergency_stop"}
    rendered = package_path.read_text(encoding="utf-8").lower()
    for forbidden in ("/estop/clear", "/joints/", "/recipes/", "raw_mega", "gcode"):
        assert forbidden not in rendered


def test_hub_artifacts_and_rfcomm_capability_gate_exist():
    required = (
        "docs/bluetooth_link.md",
        "docs/smart_home_integration.md",
        "docs/vendor_axis4ui_protocol.md",
        "scripts/bluetooth_rfcomm_probe.py",
        "scripts/unoq_bluetooth_capabilities.sh",
        "scripts/unoq_bluetooth_pair_remote.sh",
    )
    for relative in required:
        assert (ROOT / relative).is_file(), relative

    capability_script = (ROOT / "scripts/unoq_bluetooth_capabilities.sh").read_text(
        encoding="utf-8"
    )
    assert "BTPROTO_RFCOMM" in capability_script
    assert "Powered: yes" in capability_script


def test_hardware_gate_retains_transport_and_motion_blockers():
    readiness = yaml.safe_load(
        (ROOT / "config/hardware_readiness.yaml").read_text(encoding="utf-8")
    )
    items = {item["id"]: item for item in readiness["items"]}

    assert readiness["ready_for_real_motion"] is False
    assert items["pin_map"]["verified"] is True
    assert items["low_power_test"]["verified"] is True
    assert items["controller_transport"]["verified"] is False
    assert items["estop"]["verified"] is False
    assert items["axis_limits"]["verified"] is False
