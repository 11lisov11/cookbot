import pytest

from unoq_backend.models import AIPlan, AIPlanStep
from unoq_backend.safety import SafetyValidator
from unoq_backend.simulator import CookBotSimulator


def test_joint_limits_are_enforced():
    simulator = CookBotSimulator()
    simulator.enable_motion()
    simulator.home_all()
    state = simulator.snapshot()
    SafetyValidator().validate_joint_move(state, "joint_1", 45.0, 1.0)
    with pytest.raises(ValueError, match="limit_exceeded"):
        SafetyValidator().validate_joint_move(state, "joint_1", 46.0, 1.0)


def test_unknown_ai_steps_are_forbidden():
    plan = AIPlan(steps=[AIPlanStep(type="raw_mega", payload={"command": "set_joint"})])
    with pytest.raises(ValueError, match="forbidden_ai_step:raw_mega"):
        SafetyValidator().validate_ai_plan(plan)

