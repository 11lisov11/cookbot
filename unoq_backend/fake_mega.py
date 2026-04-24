import asyncio
from typing import Any

from .mega_protocol import decode_request, encode_response
from .models import MegaRequest, MegaResponse
from .simulator import CookBotSimulator


class FakeMegaDevice:
    def __init__(self, simulator: CookBotSimulator | None = None):
        self.simulator = simulator or CookBotSimulator()

    def handle(self, request: MegaRequest) -> MegaResponse:
        try:
            data = self._dispatch(request.command, request.args)
            return MegaResponse(id=request.id, ok=True, data=data)
        except ValueError as exc:
            return MegaResponse(id=request.id, ok=False, error=str(exc))

    def _dispatch(self, command: str, args: dict[str, Any]) -> dict[str, Any]:
        if command == "hello":
            return {
                "name": "CookBot Fake Mega",
                "firmware": "cookbot-fake-mega",
                "version": "0.1.0",
                "protocol_version": 1,
                "hardware_configured": False,
                "capabilities": self.simulator.capabilities(),
            }
        if command == "ping":
            return {"pong": True}
        if command == "get_capabilities":
            return {"capabilities": self.simulator.capabilities()}
        if command == "get_faults":
            return {"faults": self.simulator.faults()}
        if command == "inject_fault":
            self.simulator.inject_fault(
                str(args.get("code")),
                joint_id=args.get("joint_id"),
                message=args.get("message"),
            )
            return {"faults": self.simulator.faults(), "state": self.simulator.as_mega_data()}
        if command == "clear_faults":
            self.simulator.clear_faults()
            return {"faults": self.simulator.faults(), "state": self.simulator.as_mega_data()}
        if command == "get_state":
            return {"state": self.simulator.as_mega_data()}
        if command == "enable_motion":
            self.simulator.enable_motion()
            return {"state": self.simulator.as_mega_data()}
        if command == "home_all":
            self.simulator.home_all()
            return {"state": self.simulator.as_mega_data()}
        if command == "set_joint":
            self.simulator.move_joint(str(args.get("joint_id")), float(args.get("position")))
            return {"state": self.simulator.as_mega_data()}
        if command == "set_gripper":
            self.simulator.set_gripper(float(args.get("position")))
            return {"state": self.simulator.as_mega_data()}
        if command == "estop":
            self.simulator.estop()
            return {"state": self.simulator.as_mega_data()}
        if command == "clear_estop":
            self.simulator.clear_estop()
            return {"state": self.simulator.as_mega_data()}
        raise ValueError("unknown_command")


class FakeMegaTcpServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765, device: FakeMegaDevice | None = None):
        self.host = host
        self.port = port
        self.device = device or FakeMegaDevice()

    async def serve(self) -> None:
        server = await asyncio.start_server(self._handle_client, self.host, self.port)
        async with server:
            await server.serve_forever()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break
                try:
                    response = self.device.handle(decode_request(line))
                except Exception as exc:  # Keep the fake Mega process alive on malformed input.
                    response = MegaResponse(id="invalid", ok=False, error=f"bad_request:{exc}")
                writer.write(encode_response(response))
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()


def main() -> None:
    from .config import get_settings

    settings = get_settings()
    server = FakeMegaTcpServer(settings.fake_mega_host, settings.fake_mega_port)
    asyncio.run(server.serve())


if __name__ == "__main__":
    main()
