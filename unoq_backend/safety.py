from typing import Any

from .models import AIPlan, SystemState


ALLOWED_AI_STEPS = {"move_joint", "set_gripper", "wait", "home_all", "snapshot", "recipe_note"}
FORBIDDEN_AI_STEPS = {
    "heat",
    "set_heat",
    "knife",
    "cut",
    "relay",
    "raw_mega",
    "exec",
    "run_code",
    "autonomous_cook",
}


class SafetyValidator:
    def validate_joint_move(self, state: SystemState, joint_id: str, position: float, speed: float) -> None:
        if state.estop:
            raise ValueError("estop_active")
        if not state.motion_enabled:
            raise ValueError("motion_not_enabled")
        axis = next((item for item in state.axes if item.id == joint_id), None)
        if axis is None:
            raise ValueError("unknown_joint")
        if not axis.homed:
            raise ValueError("not_homed")
        if position < axis.min_position or position > axis.max_position:
            raise ValueError("limit_exceeded")
        if speed <= 0.0 or speed > 1.0:
            raise ValueError("invalid_speed")

    def validate_gripper(self, state: SystemState, position: float) -> None:
        if state.estop:
            raise ValueError("estop_active")
        if not state.motion_enabled:
            raise ValueError("motion_not_enabled")
        if position < 0.0 or position > 1.0:
            raise ValueError("gripper_limit_exceeded")

    def validate_home(self, state: SystemState) -> None:
        if state.estop:
            raise ValueError("estop_active")

    def validate_ai_plan(self, plan: AIPlan) -> None:
        if not plan.steps:
            raise ValueError("empty_ai_plan")
        for step in plan.steps:
            if step.type in FORBIDDEN_AI_STEPS or step.type not in ALLOWED_AI_STEPS:
                raise ValueError(f"forbidden_ai_step:{step.type}")
            self._validate_ai_step_payload(step.type, step.payload)

    def _validate_ai_step_payload(self, step_type: str, payload: dict[str, Any]) -> None:
        if step_type == "move_joint":
            joint_id = payload.get("joint_id")
            position = payload.get("position")
            if not isinstance(joint_id, str) or not isinstance(position, (int, float)):
                raise ValueError("invalid_move_joint_payload")
        if step_type == "set_gripper":
            position = payload.get("position")
            if not isinstance(position, (int, float)) or position < 0.0 or position > 1.0:
                raise ValueError("invalid_gripper_payload")
        if step_type == "wait":
            seconds = payload.get("seconds", 0)
            if not isinstance(seconds, (int, float)) or seconds < 0 or seconds > 30:
                raise ValueError("invalid_wait_payload")

