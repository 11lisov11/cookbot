import json
from pathlib import Path

from .models import (
    CalibrationAxis,
    CalibrationProfile,
    CalibrationStatus,
    CalibrationWizardStatus,
    SystemState,
)


class CalibrationStore:
    def __init__(self, path: Path):
        self.path = path

    def status(self, state: SystemState) -> CalibrationStatus:
        profile = self.load()
        return CalibrationStatus(
            loaded=profile is not None,
            path=str(self.path),
            profile=profile,
            state_axes=self._axes_from_state(state),
        )

    def save(self, state: SystemState) -> CalibrationProfile:
        profile = CalibrationProfile(axes=self._axes_from_state(state))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        return profile

    def load(self) -> CalibrationProfile | None:
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return CalibrationProfile.model_validate(data)

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def _axes_from_state(self, state: SystemState) -> list[CalibrationAxis]:
        return [
            CalibrationAxis(
                id=axis.id,
                min_position=axis.min_position,
                max_position=axis.max_position,
                homed=axis.homed,
                calibrated=axis.calibrated,
            )
            for axis in state.axes
        ]


class CalibrationWizard:
    steps = [
        ("confirm_estop", "Confirm ESTOP is available"),
        ("confirm_external_power", "Confirm motor power is separate"),
        ("confirm_no_real_motion", "Confirm no real motion outputs are enabled"),
        ("home_simulator", "Run simulator homing"),
        ("mark_simulated_calibration", "Mark simulated calibration"),
        ("save_profile", "Save calibration profile"),
    ]

    def __init__(self):
        self._status = CalibrationWizardStatus(total_steps=len(self.steps))

    def start(self) -> CalibrationWizardStatus:
        self._status = CalibrationWizardStatus(
            active=True,
            completed=False,
            current_step=0,
            total_steps=len(self.steps),
            current_step_id=self.steps[0][0],
            completed_steps=[],
            last_message="started",
        )
        return self.status()

    def status(self) -> CalibrationWizardStatus:
        return self._status.model_copy(deep=True)

    def advance(self) -> CalibrationWizardStatus:
        if not self._status.active and not self._status.completed:
            self.start()
        if self._status.completed:
            return self.status()
        step_id = self.steps[self._status.current_step][0]
        if step_id not in self._status.completed_steps:
            self._status.completed_steps.append(step_id)
        next_index = self._status.current_step + 1
        if next_index >= len(self.steps):
            self._status.active = False
            self._status.completed = True
            self._status.current_step = len(self.steps)
            self._status.current_step_id = None
            self._status.last_message = "completed"
            return self.status()
        self._status.current_step = next_index
        self._status.current_step_id = self.steps[next_index][0]
        self._status.last_message = f"advanced_to:{self._status.current_step_id}"
        return self.status()

    def reset(self) -> CalibrationWizardStatus:
        self._status = CalibrationWizardStatus(total_steps=len(self.steps), last_message="reset")
        return self.status()
