import asyncio
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unoq_backend.fake_mega import FakeMegaTcpServer
from unoq_backend.transports import TcpMegaTransport


async def main() -> None:
    server = FakeMegaTcpServer()
    tcp = await asyncio.start_server(server._handle_client, "127.0.0.1", 0)
    port = tcp.sockets[0].getsockname()[1]
    try:
        transport = TcpMegaTransport("127.0.0.1", port)
        hello = await transport.send("hello")
        assert hello.ok is True
        assert hello.data["protocol_version"] == 1
        capabilities = await transport.send("get_capabilities")
        assert capabilities.ok is True
        assert capabilities.data["capabilities"]["hardware_configured"] is False
        hardware_config = await transport.send("get_hardware_config")
        assert hardware_config.ok is True
        assert hardware_config.data["hardware_config"]["hardware_configured"] is False
        assert (await transport.send("get_limit_switches")).ok is True
        self_test = await transport.send("self_test")
        assert self_test.ok is True
        assert self_test.data["self_test"]["motion_outputs_enabled"] is False
        firmware_status = await transport.send("get_firmware_status")
        assert firmware_status.ok is True
        assert firmware_status.data["firmware_status"]["bench_outputs_enabled"] is False
        motion_profile = await transport.send("get_motion_profile")
        assert motion_profile.ok is True
        assert motion_profile.data["motion_profile"]["coordinate_mode_supported"] is False
        assert (await transport.send("read_inputs")).ok is True
        bench_unlock = await transport.send("bench_unlock", {"confirm": "BENCH_ONLY"})
        assert bench_unlock.ok is False
        assert bench_unlock.error == "bench_outputs_disabled"
        bench_test = await transport.send("bench_test_output", {"pin": 13, "duration_ms": 10})
        assert bench_test.ok is False
        assert bench_test.error == "bench_outputs_disabled"
        assert (await transport.send("ping")).data["pong"] is True
        assert (await transport.send("get_state")).ok is True
        before_home = await transport.send("set_joint", {"joint_id": "joint_1", "position": 1.0})
        assert before_home.ok is False
        assert before_home.error == "motion_not_enabled"
        assert (await transport.send("enable_motion")).ok is True
        assert (await transport.send("home_all")).ok is True
        assert (await transport.send("set_joint", {"joint_id": "joint_1", "position": 1.0})).ok is True
        over_limit = await transport.send("set_joint", {"joint_id": "joint_1", "position": 99.0})
        assert over_limit.ok is False
        assert over_limit.error == "limit_exceeded"
        estop = await transport.send("estop")
        assert estop.ok is True
        assert estop.data["state"]["queue_depth"] == 0
        assert (await transport.send("get_faults")).ok is True
        print("CookBot fake Mega smoke passed")
    finally:
        tcp.close()
        await tcp.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
