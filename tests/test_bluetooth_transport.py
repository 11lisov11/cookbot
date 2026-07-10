import json

import pytest

from unoq_backend.app import CookBotController
from unoq_backend.config import Settings
from unoq_backend.transports import BluetoothRfcommMegaTransport


class ScriptedRfcommSocket:
    def __init__(self):
        self.connected_to = None
        self.timeout = None
        self.closed = False
        self.responses = bytearray()

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def connect(self, target) -> None:
        self.connected_to = target

    def sendall(self, payload: bytes) -> None:
        request = json.loads(payload.decode("utf-8"))
        event = {"event": "watchdog", "source": "mega", "message": "test"}
        if request["command"] == "ping":
            data = {"pong": True}
        else:
            data = {"name": "CookBot Mega Bluetooth"}
        response = {"id": request["id"], "ok": True, "data": data, "error": None}
        self.responses.extend(json.dumps(event).encode("utf-8") + b"\n")
        self.responses.extend(json.dumps(response).encode("utf-8") + b"\n")

    def recv(self, size: int) -> bytes:
        chunk_size = min(size, 11, len(self.responses))
        if chunk_size == 0:
            return b""
        chunk = bytes(self.responses[:chunk_size])
        del self.responses[:chunk_size]
        return chunk

    def close(self) -> None:
        self.closed = True


class SendFailureRfcommSocket(ScriptedRfcommSocket):
    def sendall(self, payload: bytes) -> None:
        raise OSError("simulated_link_loss")


@pytest.mark.asyncio
async def test_bluetooth_rfcomm_transport_reuses_connection_and_skips_events():
    handle = ScriptedRfcommSocket()
    transport = BluetoothRfcommMegaTransport(
        "AA:BB:CC:DD:EE:FF",
        channel=1,
        timeout_s=1,
        socket_factory=lambda: handle,
    )

    hello = await transport.send("hello")
    ping = await transport.send("ping")

    assert hello.ok is True
    assert hello.data["name"] == "CookBot Mega Bluetooth"
    assert ping.data["pong"] is True
    assert handle.connected_to == ("AA:BB:CC:DD:EE:FF", 1)
    assert handle.timeout == 1
    transport.close()
    assert handle.closed is True


@pytest.mark.asyncio
async def test_bluetooth_retries_reads_but_never_replays_motion():
    read_handles = [SendFailureRfcommSocket(), ScriptedRfcommSocket()]
    read_factory_calls = 0

    def read_factory():
        nonlocal read_factory_calls
        handle = read_handles[read_factory_calls]
        read_factory_calls += 1
        return handle

    read_transport = BluetoothRfcommMegaTransport(
        "AA:BB:CC:DD:EE:FF", timeout_s=1, socket_factory=read_factory
    )
    assert (await read_transport.send("ping")).data["pong"] is True
    assert read_factory_calls == 2

    motion_factory_calls = 0

    def motion_factory():
        nonlocal motion_factory_calls
        motion_factory_calls += 1
        return SendFailureRfcommSocket()

    motion_transport = BluetoothRfcommMegaTransport(
        "AA:BB:CC:DD:EE:FF", timeout_s=1, socket_factory=motion_factory
    )
    with pytest.raises(RuntimeError, match="bluetooth_rfcomm_error"):
        await motion_transport.send("move_axis", {"axis": "A", "steps": 10})
    assert motion_factory_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("address", "error"),
    [
        (None, "bluetooth_address_not_configured"),
        ("not-a-mac", "bluetooth_address_invalid"),
    ],
)
async def test_bluetooth_rfcomm_transport_rejects_missing_or_invalid_address(address, error):
    transport = BluetoothRfcommMegaTransport(
        address,
        socket_factory=lambda: ScriptedRfcommSocket(),
    )
    with pytest.raises(RuntimeError, match=error):
        await transport.send("ping")


def test_hardware_gate_accepts_configured_bluetooth_as_a_real_transport(tmp_path):
    configured = CookBotController(
        Settings(
            mode="hardware",
            mega_transport="bluetooth_rfcomm",
            bluetooth_address="AA:BB:CC:DD:EE:FF",
            log_path=tmp_path / "cookbot.jsonl",
            hardware_readiness_path=tmp_path / "missing-readiness.yaml",
        )
    ).hardware_gate_report()
    configured_ids = {blocker.id for blocker in configured.blockers}
    assert "mega_transport_not_hardware" not in configured_ids
    assert "bluetooth_address_missing" not in configured_ids

    missing_address = CookBotController(
        Settings(
            mode="hardware",
            mega_transport="bluetooth_rfcomm",
            log_path=tmp_path / "cookbot-missing.jsonl",
            hardware_readiness_path=tmp_path / "missing-readiness.yaml",
        )
    ).hardware_gate_report()
    assert "bluetooth_address_missing" in {blocker.id for blocker in missing_address.blockers}


def test_public_settings_report_bluetooth_without_exposing_mac(tmp_path):
    controller = CookBotController(
        Settings(
            mega_transport="bluetooth_rfcomm",
            bluetooth_address="AA:BB:CC:DD:EE:FF",
            bluetooth_channel=3,
            log_path=tmp_path / "cookbot.jsonl",
        )
    )
    public = controller.public_settings().model_dump()
    assert public["bluetooth_configured"] is True
    assert public["bluetooth_channel"] == 3
    assert "AA:BB:CC:DD:EE:FF" not in json.dumps(public)
