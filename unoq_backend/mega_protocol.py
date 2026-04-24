import json
from typing import Any
from uuid import uuid4

from .models import MegaRequest, MegaResponse


def build_request(command: str, args: dict[str, Any] | None = None) -> MegaRequest:
    return MegaRequest(id=str(uuid4()), command=command, args=args or {})


def encode_request(request: MegaRequest) -> bytes:
    return (request.model_dump_json() + "\n").encode("utf-8")


def encode_response(response: MegaResponse) -> bytes:
    return (response.model_dump_json() + "\n").encode("utf-8")


def decode_request(line: bytes | str) -> MegaRequest:
    payload = line.decode("utf-8") if isinstance(line, bytes) else line
    return MegaRequest.model_validate(json.loads(payload))


def decode_response(line: bytes | str) -> MegaResponse:
    payload = line.decode("utf-8") if isinstance(line, bytes) else line
    return MegaResponse.model_validate(json.loads(payload))

