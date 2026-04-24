import json
from types import SimpleNamespace

from unoq_backend.ai import OpenAICompatibleClient


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"steps": [{"type": "snapshot", "payload": {}}], "notes": "ok"}
                            )
                        }
                    }
                ]
            }
        ).encode("utf-8")


def test_openai_compatible_client_parses_strict_plan(monkeypatch):
    captured = SimpleNamespace(request=None)

    def fake_urlopen(request, timeout):
        captured.request = request
        assert timeout == 30
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = OpenAICompatibleClient("https://api.example.test/v1", "test-key", "test-model")
    plan = client.plan("look", include_snapshot=True, snapshot_data_url="data:image/svg+xml;base64,abc")

    assert plan.steps[0].type == "snapshot"
    assert captured.request.full_url == "https://api.example.test/v1/chat/completions"
    assert captured.request.headers["Authorization"] == "Bearer test-key"
    body = json.loads(captured.request.data.decode("utf-8"))
    user_payload = json.loads(body["messages"][1]["content"])
    assert user_payload["snapshot_data_url"] == "data:image/svg+xml;base64,abc"
