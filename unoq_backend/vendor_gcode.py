import math
import re
from dataclasses import dataclass, field

from .models import (
    VendorGCodeCommand,
    VendorGCodeValidationResponse,
    VendorProfileResponse,
)


DEFAULT_COORDINATES = {"X": 0.0, "Y": 205.0, "Z": 135.0, "E": -500.0}
DEFAULT_FEED_MM_S = 100.0
MIN_FEED_MM_S = 5.0
MAX_FEED_MM_S = 150.0

G_COMMANDS = {
    1: "linear_move",
    4: "dwell",
    90: "absolute_mode",
    91: "relative_mode",
    92: "set_position",
    2696: "vendor_calibration_reset",
}

M_COMMANDS = {
    11: "ambiguous_auxiliary_a",
    12: "ambiguous_auxiliary_b",
    14: "vacuum_on",
    15: "vacuum_off",
    26: "gripper_on",
    27: "gripper_off",
    61: "execution_high",
    62: "execution_low",
    211: "cooling_fan_on",
    212: "cooling_fan_off",
    6216: "driver_enable_on",
    6228: "driver_enable_off",
}

_COMMAND_RE = re.compile(r"^([GM])\s*(\d+)(.*)$", re.IGNORECASE)
_WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.IGNORECASE)
_PARAMETER_ORDER = ("X", "Y", "Z", "E", "F", "S")


def parse_vendor_gcode(line: str) -> VendorGCodeCommand:
    if len(line) > 256:
        raise ValueError("command_too_long")
    stripped = line.rstrip("\r\n").strip()
    if not stripped:
        raise ValueError("empty_command")
    if ";" in stripped or "(" in stripped or ")" in stripped:
        raise ValueError("comments_not_supported")

    command_match = _COMMAND_RE.fullmatch(stripped)
    if command_match is None:
        raise ValueError("invalid_command_syntax")

    family = command_match.group(1).upper()
    code = int(command_match.group(2))
    parameters = _parse_parameters(command_match.group(3))

    if family == "G":
        name = G_COMMANDS.get(code)
        if name is None:
            raise ValueError("unsupported_g_code")
        _validate_g_code(code, parameters)
    else:
        name = M_COMMANDS.get(code)
        if name is None:
            raise ValueError("unsupported_m_code")
        if parameters:
            raise ValueError("m_code_parameters_not_supported")

    normalized = f"{family}{code}"
    for key in _PARAMETER_ORDER:
        if key in parameters:
            normalized += f" {key}{_format_number(parameters[key])}"

    return VendorGCodeCommand(
        family=family,
        code=code,
        name=name,
        parameters=parameters,
        normalized=normalized,
    )


def validate_vendor_gcode(line: str) -> VendorGCodeValidationResponse:
    try:
        command = parse_vendor_gcode(line)
    except ValueError as exc:
        return VendorGCodeValidationResponse(
            accepted=False,
            rejected_reason=str(exc),
        )
    return VendorGCodeValidationResponse(accepted=True, command=command)


def vendor_profile() -> VendorProfileResponse:
    return VendorProfileResponse(
        source="AXIS4UI 1.12 bytecode + RA Pendant 1.01 APK",
        transport={
            "desktop": "serial_115200_ascii_cr",
            "android": "bluetooth_classic_spp_rfcomm_ascii_cr",
            "desktop_program_line_delay_ms": 500,
            "desktop_waits_for_motion_complete": False,
        },
        coordinate_defaults=dict(DEFAULT_COORDINATES),
        feed_mm_s={"minimum": MIN_FEED_MM_S, "default": DEFAULT_FEED_MM_S, "maximum": MAX_FEED_MM_S},
        commands={
            "linear_move": "G1 X{x} Y{y} Z{z} E{e} F{feed}",
            "dwell": "G4 S{seconds}",
            "absolute_mode": "G90",
            "relative_mode": "G91",
            "set_position": "G92 X{x} Y{y} Z{z} E{e}",
            "vendor_calibration_reset": "G2696",
            **{name: f"M{code}" for code, name in M_COMMANDS.items()},
        },
        missing_controller_parameters=[
            "motor_full_steps_per_revolution",
            "a4988_microstep_jumper_state_per_axis",
            "a4988_rsense_and_vref_per_axis",
            "steps_per_degree_for_a_b_c",
            "steps_per_mm_and_transmission_pitch_for_slider_e",
            "arm_link_dimensions_and_inverse_kinematics",
            "acceleration_and_max_step_rate_per_axis",
            "safe_coordinate_workspace_and_collision_envelope",
            "complete_feedback_and_error_grammar",
        ],
    )


@dataclass
class VendorMachineState:
    coordinates: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_COORDINATES))
    feed_mm_s: float = DEFAULT_FEED_MM_S
    absolute_mode: bool = True
    outputs: dict[str, bool] = field(
        default_factory=lambda: {
            "drivers": False,
            "fan": False,
            "vacuum": False,
            "gripper": False,
            "execution": False,
            "auxiliary_a": False,
            "auxiliary_b": False,
        }
    )
    calibration_requested: bool = False


@dataclass
class VendorExecutionResult:
    command: VendorGCodeCommand
    state: VendorMachineState
    response_line: str


class VendorControllerEmulator:
    """Behavioral emulator only; it never opens serial ports or drives hardware."""

    def __init__(self) -> None:
        self.state = VendorMachineState()

    def execute(self, line: str) -> VendorExecutionResult:
        command = parse_vendor_gcode(line)
        if command.family == "G":
            self._execute_g(command)
        else:
            self._execute_m(command)
        return VendorExecutionResult(
            command=command,
            state=self._copy_state(),
            response_line=self.feedback_line(),
        )

    def feedback_line(self) -> str:
        coordinate_text = " ".join(
            f"{axis}{_format_number(self.state.coordinates[axis])}"
            for axis in ("X", "Y", "Z", "E")
        )
        return f"ok {coordinate_text}.\n"

    def _execute_g(self, command: VendorGCodeCommand) -> None:
        if command.code == 1:
            for axis in ("X", "Y", "Z", "E"):
                if axis not in command.parameters:
                    continue
                value = command.parameters[axis]
                if self.state.absolute_mode:
                    self.state.coordinates[axis] = value
                else:
                    self.state.coordinates[axis] += value
            if "F" in command.parameters:
                self.state.feed_mm_s = command.parameters["F"]
        elif command.code == 90:
            self.state.absolute_mode = True
        elif command.code == 91:
            self.state.absolute_mode = False
        elif command.code == 92:
            for axis in ("X", "Y", "Z", "E"):
                if axis in command.parameters:
                    self.state.coordinates[axis] = command.parameters[axis]
        elif command.code == 2696:
            # The vendor apps expose this command but do not reveal its controller semantics.
            self.state.calibration_requested = True

    def _execute_m(self, command: VendorGCodeCommand) -> None:
        assignments = {
            11: ("auxiliary_a", True),
            12: ("auxiliary_a", False),
            14: ("vacuum", True),
            15: ("vacuum", False),
            26: ("gripper", True),
            27: ("gripper", False),
            61: ("execution", True),
            62: ("execution", False),
            211: ("fan", True),
            212: ("fan", False),
            6216: ("drivers", True),
            6228: ("drivers", False),
        }
        output, value = assignments[command.code]
        self.state.outputs[output] = value

    def _copy_state(self) -> VendorMachineState:
        return VendorMachineState(
            coordinates=dict(self.state.coordinates),
            feed_mm_s=self.state.feed_mm_s,
            absolute_mode=self.state.absolute_mode,
            outputs=dict(self.state.outputs),
            calibration_requested=self.state.calibration_requested,
        )


def _parse_parameters(tail: str) -> dict[str, float]:
    parameters: dict[str, float] = {}
    cursor = 0
    while cursor < len(tail):
        while cursor < len(tail) and tail[cursor].isspace():
            cursor += 1
        if cursor >= len(tail):
            break
        match = _WORD_RE.match(tail, cursor)
        if match is None:
            raise ValueError("invalid_parameter_syntax")
        key = match.group(1).upper()
        if key in parameters:
            raise ValueError("duplicate_parameter")
        value = float(match.group(2))
        if not math.isfinite(value):
            raise ValueError("non_finite_parameter")
        parameters[key] = value
        cursor = match.end()
    return parameters


def _validate_g_code(code: int, parameters: dict[str, float]) -> None:
    keys = set(parameters)
    if code == 1:
        if not keys.intersection({"X", "Y", "Z", "E"}):
            raise ValueError("linear_move_requires_axis")
        if not keys.issubset({"X", "Y", "Z", "E", "F"}):
            raise ValueError("unsupported_linear_move_parameter")
        if "F" in parameters and not MIN_FEED_MM_S <= parameters["F"] <= MAX_FEED_MM_S:
            raise ValueError("feed_out_of_vendor_range")
        return
    if code == 4:
        if keys != {"S"}:
            raise ValueError("dwell_requires_seconds")
        if parameters["S"] < 0.0 or parameters["S"] > 3600.0:
            raise ValueError("dwell_out_of_range")
        return
    if code == 92:
        if not keys or not keys.issubset({"X", "Y", "Z", "E"}):
            raise ValueError("set_position_requires_axes")
        return
    if parameters:
        raise ValueError("g_code_parameters_not_supported")


def _format_number(value: float) -> str:
    if value == 0:
        return "0"
    return f"{value:.6f}".rstrip("0").rstrip(".")
