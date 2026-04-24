import asyncio
from abc import ABC, abstractmethod
from typing import Any

from .fake_mega import FakeMegaDevice
from .mega_protocol import build_request, decode_response, encode_request
from .models import MegaResponse


class MegaTransport(ABC):
    @abstractmethod
    async def send(self, command: str, args: dict[str, Any] | None = None) -> MegaResponse:
        raise NotImplementedError


class LocalFakeMegaTransport(MegaTransport):
    def __init__(self, device: FakeMegaDevice):
        self.device = device

    async def send(self, command: str, args: dict[str, Any] | None = None) -> MegaResponse:
        return self.device.handle(build_request(command, args))


class TcpMegaTransport(MegaTransport):
    def __init__(self, host: str, port: int, timeout_s: float = 2.0):
        self.host = host
        self.port = port
        self.timeout_s = timeout_s

    async def send(self, command: str, args: dict[str, Any] | None = None) -> MegaResponse:
        request = build_request(command, args)
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port), timeout=self.timeout_s
        )
        try:
            writer.write(encode_request(request))
            await writer.drain()
            line = await asyncio.wait_for(reader.readline(), timeout=self.timeout_s)
            return decode_response(line)
        finally:
            writer.close()
            await writer.wait_closed()


class SerialMegaTransport(MegaTransport):
    def __init__(self, port: str, baud: int):
        self.port = port
        self.baud = baud

    async def send(self, command: str, args: dict[str, Any] | None = None) -> MegaResponse:
        try:
            import serial  # type: ignore
        except ImportError as exc:
            raise RuntimeError("pyserial_not_installed") from exc

        request = build_request(command, args)

        def exchange() -> MegaResponse:
            with serial.Serial(self.port, self.baud, timeout=2.0) as handle:
                handle.write(encode_request(request))
                line = handle.readline()
                return decode_response(line)

        return await asyncio.to_thread(exchange)

