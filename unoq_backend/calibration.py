import json
from pathlib import Path

from .models import CalibrationAxis, CalibrationProfile, CalibrationStatus, SystemState


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

