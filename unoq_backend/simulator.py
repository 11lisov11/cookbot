from copy import deepcopy
from typing import Any

from .models import AxisState, GripperState, SystemState, utc_now


SAFE_SIMULATED_AXES = [
    AxisState(id="joint_1", min_position=-45.0, max_position=45.0),
    AxisState(id="joint_2", min_position=-45.0, max_position=45.0),
    AxisState(id="joint_3", min_position=-45.0, max_position=45.0),
]


class CookBotSimulator:
    def __init__(self, mode: str = "simulator"):
        self._faults: dict[str, str] = {}
        self._bench_unlocked = False
        self._state = SystemState(
            mode=mode,
            services={
                "backend": "ok",
                "mega": "fake",
                "camera": "mock",
                "ai": "mock",
                "vpn": "not_required",
            },
            axes=[axis.model_copy(deep=True) for axis in SAFE_SIMULATED_AXES],
            gripper=GripperState(),
        )
        self._refresh()

    def snapshot(self) -> SystemState:
        self._refresh()
        return deepcopy(self._state)

    def set_service(self, name: str, status: str) -> None:
        self._state.services[name] = status
        self._refresh()

    def enable_motion(self) -> None:
        self._raise_if_faulted()
        if self._state.estop:
            raise ValueError("estop_active")
        self._state.motion_enabled = True
        self._state.last_error = None
        self._refresh()

    def home_all(self) -> None:
        self._raise_if_faulted()
        if self._state.estop:
            raise ValueError("estop_active")
        for axis in self._state.axes:
            axis.commanded_position = 0.0
            axis.homed = True
            axis.limit_min = False
            axis.limit_max = False
        self._state.gripper.position = 0.0
        self._state.gripper.homed = True
        self._state.last_error = None
        self._refresh()

    def mark_simulated_calibration(self) -> None:
        for axis in self._state.axes:
            axis.calibrated = True
        self._state.gripper.calibrated = True
        self._refresh()

    def reset_calibration(self) -> None:
        for axis in self._state.axes:
            axis.calibrated = False
        self._state.gripper.calibrated = False
        self._refresh()

    def move_joint(self, joint_id: str, position: float) -> None:
        axis = self._axis(joint_id)
        self._raise_if_faulted()
        if self._state.estop:
            raise ValueError("estop_active")
        if not self._state.motion_enabled:
            raise ValueError("motion_not_enabled")
        if not axis.homed:
            raise ValueError("not_homed")
        if position < axis.min_position or position > axis.max_position:
            raise ValueError("limit_exceeded")
        axis.commanded_position = position
        axis.limit_min = position <= axis.min_position
        axis.limit_max = position >= axis.max_position
        self._state.last_error = None
        self._refresh()

    def set_gripper(self, position: float) -> None:
        self._raise_if_faulted()
        if self._state.estop:
            raise ValueError("estop_active")
        if not self._state.motion_enabled:
            raise ValueError("motion_not_enabled")
        if position < 0.0 or position > 1.0:
            raise ValueError("gripper_limit_exceeded")
        self._state.gripper.position = position
        self._state.last_error = None
        self._refresh()

    def estop(self) -> None:
        self._state.estop = True
        self._state.motion_enabled = False
        self._state.queue_depth = 0
        self._state.last_error = "estop_active"
        self._refresh()

    def clear_estop(self) -> None:
        self._state.estop = False
        self._state.motion_enabled = False
        for axis in self._state.axes:
            axis.homed = False
        self._state.gripper.homed = False
        self._state.last_error = "rehome_required_after_estop"
        self._refresh()

    def inject_fault(self, code: str, joint_id: str | None = None, message: str | None = None) -> None:
        detail = message or code
        self._faults[code] = detail
        self._state.motion_enabled = False
        self._state.queue_depth = 0
        self._state.last_error = code
        self._bench_unlocked = False
        if joint_id:
            axis = self._axis(joint_id)
            if "min" in code:
                axis.limit_min = True
            if "max" in code:
                axis.limit_max = True
        self._refresh()

    def clear_faults(self) -> None:
        self._faults.clear()
        for axis in self._state.axes:
            axis.limit_min = False
            axis.limit_max = False
        self._state.motion_enabled = False
        self._state.last_error = "faults_cleared_rehome_required"
        self._refresh()

    def faults(self) -> dict[str, str]:
        return dict(self._faults)

    def as_mega_data(self) -> dict[str, Any]:
        return self.snapshot().model_dump(mode="json")

    def capabilities(self) -> dict[str, Any]:
        return {
            "protocol_version": 1,
            "firmware": "cookbot-fake-mega",
            "version": "0.3.0",
            "hardware_configured": False,
            "motion_commands_enabled": True,
            "bench_outputs_enabled": False,
            "supported_commands": [
                "hello",
                "ping",
                "get_state",
                "get_capabilities",
                "get_hardware_config",
                "get_limit_switches",
                "self_test",
                "get_firmware_status",
                "get_motion_profile",
                "read_inputs",
                "bench_unlock",
                "bench_test_output",
                "get_faults",
                "inject_fault",
                "clear_faults",
                "enable_motion",
                "home_all",
                "set_joint",
                "set_gripper",
                "estop",
                "clear_estop",
            ],
        }

    def hardware_config(self) -> dict[str, Any]:
        return {
            "hardware_configured": False,
            "bench_outputs_enabled": False,
            "axis_count": 0,
            "limit_switch_count": 0,
            "estop_pin": -1,
            "gripper_pin": -1,
            "axis_pin_configured": False,
            "note": "fake_mega_placeholder_real_motion_locked",
        }

    def limit_switches(self) -> dict[str, Any]:
        return {"configured": False, "switches": self.snapshot().limit_switches}

    def self_test(self) -> dict[str, Any]:
        return {
            "ok": True,
            "hardware_configured": False,
            "bench_outputs_enabled": False,
            "motion_outputs_enabled": False,
            "checks": [
                {"id": "backend_simulator", "ok": True},
                {"id": "hardware_config", "ok": True, "detail": "placeholder"},
                {"id": "motion_outputs", "ok": True, "detail": "fake_transport_only"},
                {"id": "bench_outputs", "ok": True, "detail": "disabled"},
            ],
        }

    def firmware_status(self) -> dict[str, Any]:
        return {
            "firmware": "cookbot-fake-mega",
            "version": "0.3.0",
            "hardware_configured": False,
            "bench_outputs_enabled": False,
            "bench_unlocked": self._bench_unlocked,
            "estop": self._state.estop,
            "motion_enabled": self._state.motion_enabled,
            "watchdog_timeout_ms": 1500,
        }

    def motion_profile(self) -> dict[str, Any]:
        return {
            "coordinate_mode_supported": False,
            "vendor_gcode_supported": False,
            "microstep_config_verified": False,
            "coordinate_calibration_verified": False,
            "profiles": [],
        }

    def read_inputs(self) -> dict[str, Any]:
        return {
            "estop_pin": -1,
            "estop_active": self._state.estop,
            "limit_switches": [],
        }

    def bench_unlock(self, confirm: str | None) -> dict[str, Any]:
        if self._state.estop:
            raise ValueError("estop_active")
        if confirm != "BENCH_ONLY":
            raise ValueError("bench_confirm_required")
        raise ValueError("bench_outputs_disabled")

    def bench_test_output(self, pin: int | None, duration_ms: int | None) -> dict[str, Any]:
        if self._state.estop:
            self._bench_unlocked = False
            raise ValueError("estop_active")
        raise ValueError("bench_outputs_disabled")

    def _axis(self, joint_id: str) -> AxisState:
        for axis in self._state.axes:
            if axis.id == joint_id:
                return axis
        raise ValueError("unknown_joint")

    def _raise_if_faulted(self) -> None:
        if self._faults:
            first = next(iter(self._faults))
            raise ValueError(f"active_fault:{first}")

    def _refresh(self) -> None:
        self._state.homed = all(axis.homed for axis in self._state.axes)
        self._state.calibrated = all(axis.calibrated for axis in self._state.axes)
        switches: dict[str, bool] = {}
        for axis in self._state.axes:
            switches[f"{axis.id}_min"] = axis.limit_min
            switches[f"{axis.id}_max"] = axis.limit_max
        self._state.limit_switches = switches
        self._state.updated_at = utc_now()
