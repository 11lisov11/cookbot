import json
import urllib.request

from .models import AIPlan, AIPlanStep


FORBIDDEN_PROMPT_WORDS = {
    "cook",
    "fry",
    "boil",
    "heat",
    "knife",
    "relay",
    "raw mega",
    "execute code",
    "яичница",
    "приготовь",
    "нагрев",
}


class MockAIClient:
    def plan(
        self, command: str, include_snapshot: bool = True, snapshot_data_url: str | None = None
    ) -> AIPlan:
        lowered = command.lower()
        if any(word in lowered for word in FORBIDDEN_PROMPT_WORDS):
            return AIPlan(
                steps=[AIPlanStep(type="heat", payload={"target": "pan"})],
                notes="Mock AI intentionally proposes a forbidden step so CookBot safety can reject it.",
            )
        if "gripper" in lowered or "хват" in lowered:
            return AIPlan(
                steps=[AIPlanStep(type="set_gripper", payload={"position": 0.5})],
                notes="Mock AI gripper plan.",
            )
        return AIPlan(
            steps=[
                AIPlanStep(type="snapshot", payload={}),
                AIPlanStep(type="recipe_note", payload={"text": "No autonomous cooking started."}),
            ],
            notes="Mock AI observation-only plan.",
        )


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str | None, model: str):
        if not api_key:
            raise ValueError("ai_api_key_missing")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def plan(
        self, command: str, include_snapshot: bool = True, snapshot_data_url: str | None = None
    ) -> AIPlan:
        body = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are CookBot AI planning assistant. Return only JSON with a 'steps' array. "
                        "Allowed step types: move_joint, set_gripper, wait, home_all, snapshot, recipe_note. "
                        "Never include heat, relay, knife, raw_mega, code execution, or autonomous cooking."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "command": command,
                            "include_snapshot": include_snapshot,
                            "snapshot_data_url": snapshot_data_url if include_snapshot else None,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        return AIPlan.model_validate(json.loads(content))
