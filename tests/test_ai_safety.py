from unoq_backend.ai import MockAIClient
from unoq_backend.safety import SafetyValidator


def test_mock_ai_observation_plan_is_allowed():
    plan = MockAIClient().plan("look at the workspace")
    SafetyValidator().validate_ai_plan(plan)


def test_forbidden_ai_command_is_rejected_by_api(client):
    response = client.post("/ai/command", json={"command": "cook scrambled eggs"})
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert body["rejected_reason"] == "forbidden_ai_step:heat"


def test_gripper_ai_command_is_allowed(client):
    response = client.post("/ai/command", json={"command": "move gripper halfway"})
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["plan"]["steps"][0]["type"] == "set_gripper"

