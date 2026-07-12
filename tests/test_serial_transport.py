import json

import pytest

from unoq_backend.transports import SerialMegaTransport


class FakeSerialHandle:
    def __init__(self):
        self.closed = False
        self.lines: list[bytes] = []
        self.writes: list[dict] = []

    def reset_input_buffer(self) -> None:
        self.lines.clear()

    def write(self, payload: bytes) -> None:
        request = json.loads(payload.decode("utf-8"))
        self.writes.append(request)
        self.lines.extend(
            [
                b'{"event":"boot","detail":"ready"}\n',
                (
                    json.dumps(
                        {
                            "id": request["id"],
                            "ok": True,
                            "data": {"command": request["command"]},
                            "error": None,
                        }
                    )
                    + "\n"
                ).encode("utf-8"),
            ]
        )

    def flush(self) -> None:
        return None

    def readline(self) -> bytes:
        return self.lines.pop(0) if self.lines else b""

    def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_serial_transport_reuses_one_handle_and_ignores_events():
    handle = FakeSerialHandle()
    factory_calls: list[tuple[str, int, float]] = []

    def factory(port: str, baud: int, timeout: float):
        factory_calls.append((port, baud, timeout))
        return handle

    transport = SerialMegaTransport(
        "COM6",
        115200,
        timeout_s=0.1,
        serial_factory=factory,
        reset_wait_s=0,
    )
    ping = await transport.send("ping")
    state = await transport.send("get_state")

    assert ping.ok is True
    assert state.ok is True
    assert [request["command"] for request in handle.writes] == ["ping", "get_state"]
    assert factory_calls == [("COM6", 115200, 0.1)]

    transport.close()
    assert handle.closed is True
