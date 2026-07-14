import asyncio

import pytest

from unoq_backend.fake_mega import FakeMegaDevice, FakeMegaTcpServer
from unoq_backend.mega_protocol import build_request, decode_request, decode_response, encode_request, encode_response
from unoq_backend.models import MegaResponse
from unoq_backend.transports import TcpMegaTransport


def test_protocol_round_trip():
    request = build_request("ping")
    assert decode_request(encode_request(request)) == request
    response = MegaResponse(id=request.id, ok=True, data={"pong": True})
    assert decode_response(encode_response(response)) == response


def test_fake_mega_motion_lifecycle():
    device = FakeMegaDevice()
    hello = device.handle(build_request("hello"))
    assert hello.ok is True
    assert hello.data["protocol_version"] == 1
    assert hello.data["capabilities"]["hardware_configured"] is False
    capabilities = device.handle(build_request("get_capabilities"))
    assert capabilities.ok is True
    assert "set_joint" in capabilities.data["capabilities"]["supported_commands"]
    assert "get_firmware_status" in capabilities.data["capabilities"]["supported_commands"]
    firmware_status = device.handle(build_request("get_firmware_status"))
    assert firmware_status.ok is True
    assert firmware_status.data["firmware_status"]["bench_outputs_enabled"] is False
    motion_profile = device.handle(build_request("get_motion_profile"))
    assert motion_profile.ok is True
    assert motion_profile.data["motion_profile"]["coordinate_mode_supported"] is False
    assert motion_profile.data["motion_profile"]["microstep_config_verified"] is False
    assert motion_profile.data["motion_profile"]["supported_ramp_profiles"] == ["trapezoid", "s_curve"]
    inputs = device.handle(build_request("read_inputs"))
    assert inputs.ok is True
    bench_unlock = device.handle(build_request("bench_unlock", {"confirm": "BENCH_ONLY"}))
    assert bench_unlock.ok is False
    assert bench_unlock.error == "bench_outputs_disabled"
    bench_test = device.handle(build_request("bench_test_output", {"pin": 13, "duration_ms": 10}))
    assert bench_test.ok is False
    assert bench_test.error == "bench_outputs_disabled"
    assert device.handle(build_request("set_joint", {"joint_id": "joint_1", "position": 1})).error == "motion_not_enabled"
    assert device.handle(build_request("enable_motion")).ok is True
    assert device.handle(build_request("home_all")).ok is True
    assert device.handle(build_request("set_joint", {"joint_id": "joint_1", "position": 1})).ok is True
    assert device.handle(build_request("set_joint", {"joint_id": "joint_1", "position": 99})).error == "limit_exceeded"
    estop = device.handle(build_request("estop"))
    assert estop.ok is True
    assert estop.data["state"]["queue_depth"] == 0


def test_fake_mega_fault_injection_blocks_motion():
    device = FakeMegaDevice()
    assert device.handle(build_request("enable_motion")).ok is True
    assert device.handle(build_request("home_all")).ok is True
    fault = device.handle(build_request("inject_fault", {"code": "limit_switch_stuck_min", "joint_id": "joint_1"}))
    assert fault.ok is True
    assert fault.data["state"]["last_error"] == "limit_switch_stuck_min"
    blocked = device.handle(build_request("set_joint", {"joint_id": "joint_1", "position": 1}))
    assert blocked.ok is False
    assert blocked.error == "active_fault:limit_switch_stuck_min"
    cleared = device.handle(build_request("clear_faults"))
    assert cleared.ok is True
    assert cleared.data["faults"] == {}


@pytest.mark.asyncio
async def test_fake_mega_tcp_transport():
    server = FakeMegaTcpServer()
    tcp = await asyncio.start_server(server._handle_client, "127.0.0.1", 0)
    port = tcp.sockets[0].getsockname()[1]
    try:
        transport = TcpMegaTransport("127.0.0.1", port)
        hello = await transport.send("hello")
        assert hello.ok is True
        assert hello.data["name"] == "CookBot Fake Mega"
        ping = await transport.send("ping")
        assert ping.ok is True
        assert ping.data["pong"] is True
    finally:
        tcp.close()
        await tcp.wait_closed()
