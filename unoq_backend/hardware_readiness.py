from pathlib import Path

import yaml

from .models import HardwareReadinessItem, HardwareReadinessResponse


class HardwareReadinessStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> HardwareReadinessResponse:
        if not self.path.exists():
            return HardwareReadinessResponse(items=self._default_items())
        data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        response = HardwareReadinessResponse.model_validate(data)
        response.ready_for_real_motion = bool(response.items) and all(item.verified for item in response.items)
        return response

    def _default_items(self) -> list[HardwareReadinessItem]:
        return [
            HardwareReadinessItem(id="pin_map", label="Mega pin map verified"),
            HardwareReadinessItem(id="controller_transport", label="Mega to UNO Q transport verified"),
            HardwareReadinessItem(id="driver_types", label="Motor/servo driver types identified"),
            HardwareReadinessItem(id="limit_polarity", label="Limit switch polarity verified"),
            HardwareReadinessItem(id="external_power", label="External motor power and common ground verified"),
            HardwareReadinessItem(id="estop", label="Hardware ESTOP verified"),
            HardwareReadinessItem(id="axis_limits", label="Axis min/max limits measured"),
            HardwareReadinessItem(id="homing_direction", label="Safe homing direction verified for each axis"),
            HardwareReadinessItem(id="low_power_test", label="Low-power motion test completed"),
        ]
