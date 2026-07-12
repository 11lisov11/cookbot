import asyncio
import re
import socket
import time
from abc import ABC, abstractmethod
from typing import Any, Callable

from .fake_mega import FakeMegaDevice
from .mega_protocol import build_request, decode_response, encode_request
from .models import MegaResponse


class MegaTransport(ABC):
    @abstractmethod
    async def send(self, command: str, args: dict[str, Any] | None = None) -> MegaResponse:
        raise NotImplementedError

    def close(self) -> None:
        return None


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
    """Persistent USB serial transport that does not reset Mega per command."""

    _RETRY_SAFE_COMMANDS = frozenset(
        {
            "hello",
            "ping",
            "get_state",
            "get_capabilities",
            "get_hardware_config",
            "get_limit_switches",
            "self_test",
            "get_firmware_status",
            "read_inputs",
            "get_faults",
            "estop",
        }
    )

    def __init__(
        self,
        port: str,
        baud: int,
        timeout_s: float = 2.0,
        serial_factory: Callable[..., Any] | None = None,
        reset_wait_s: float = 2.0,
    ):
        self.port = port
        self.baud = baud
        self.timeout_s = timeout_s
        self._serial_factory = serial_factory
        self._reset_wait_s = reset_wait_s
        self._handle: Any | None = None
        self._lock = asyncio.Lock()

    async def send(self, command: str, args: dict[str, Any] | None = None) -> MegaResponse:
        request = build_request(command, args)
        payload = encode_request(request)
        async with self._lock:
            return await asyncio.to_thread(
                self._exchange_with_retry,
                command,
                request.id,
                payload,
            )

    def close(self) -> None:
        self._close_handle()

    def _exchange_with_retry(self, command: str, request_id: str, payload: bytes) -> MegaResponse:
        last_error: Exception | None = None
        attempts = 2 if command in self._RETRY_SAFE_COMMANDS else 1
        for _attempt in range(attempts):
            try:
                handle = self._ensure_handle()
                handle.write(payload)
                flush = getattr(handle, "flush", None)
                if flush is not None:
                    flush()
                return self._read_matching_response(handle, request_id)
            except Exception as exc:
                last_error = exc
                self._close_handle()
        assert last_error is not None
        if isinstance(last_error, RuntimeError) and str(last_error).startswith("serial_"):
            raise last_error
        raise RuntimeError(f"serial_transport_error:{last_error}") from last_error

    def _ensure_handle(self):
        if self._handle is not None:
            return self._handle
        if self._serial_factory is None:
            try:
                import serial  # type: ignore
            except ImportError as exc:
                raise RuntimeError("serial_pyserial_not_installed") from exc
            factory = serial.Serial
        else:
            factory = self._serial_factory

        try:
            handle = factory(self.port, self.baud, timeout=self.timeout_s)
        except Exception as exc:
            raise RuntimeError(f"serial_open_failed:{self.port}:{exc}") from exc
        self._handle = handle
        if self._reset_wait_s > 0:
            time.sleep(self._reset_wait_s)
        reset_input = getattr(handle, "reset_input_buffer", None)
        if reset_input is not None:
            reset_input()
        return handle

    def _read_matching_response(self, handle, request_id: str) -> MegaResponse:
        deadline = time.monotonic() + self.timeout_s
        while time.monotonic() < deadline:
            line = handle.readline()
            if not line:
                continue
            try:
                response = decode_response(line)
            except Exception:
                # Boot/watchdog events are valid NDJSON but not MegaResponse.
                continue
            if response.id == request_id:
                return response
        raise TimeoutError("serial_response_timeout")

    def _close_handle(self) -> None:
        handle = self._handle
        self._handle = None
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass


class BluetoothRfcommMegaTransport(MegaTransport):
    """Persistent Bluetooth Classic SPP transport for the UNO Q Linux side."""

    _MAC_PATTERN = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
    _RETRY_SAFE_COMMANDS = frozenset(
        {
            "hello",
            "ping",
            "get_state",
            "get_capabilities",
            "get_hardware_config",
            "get_limit_switches",
            "self_test",
            "get_firmware_status",
            "read_inputs",
            "get_faults",
            "estop",
        }
    )

    def __init__(
        self,
        address: str | None,
        channel: int = 1,
        timeout_s: float = 3.0,
        socket_factory: Callable[[], Any] | None = None,
    ):
        self.address = (address or "").strip().upper()
        self.channel = channel
        self.timeout_s = timeout_s
        self._socket_factory = socket_factory
        self._socket: Any | None = None
        self._receive_buffer = bytearray()
        self._lock = asyncio.Lock()

    async def send(self, command: str, args: dict[str, Any] | None = None) -> MegaResponse:
        request = build_request(command, args)
        payload = encode_request(request)
        async with self._lock:
            return await asyncio.to_thread(
                self._exchange_with_retry,
                command,
                request.id,
                payload,
            )

    def close(self) -> None:
        self._close_socket()

    def _exchange_with_retry(self, command: str, request_id: str, payload: bytes) -> MegaResponse:
        last_error: Exception | None = None
        attempts = 2 if command in self._RETRY_SAFE_COMMANDS else 1
        for _attempt in range(attempts):
            try:
                handle = self._ensure_socket()
                handle.sendall(payload)
                return self._read_matching_response(handle, request_id)
            except Exception as exc:
                last_error = exc
                self._close_socket()
        assert last_error is not None
        if isinstance(last_error, RuntimeError) and str(last_error).startswith("bluetooth_"):
            raise last_error
        raise RuntimeError(f"bluetooth_rfcomm_error:{last_error}") from last_error

    def _ensure_socket(self):
        if self._socket is not None:
            return self._socket
        if not self.address:
            raise RuntimeError("bluetooth_address_not_configured")
        if not self._MAC_PATTERN.fullmatch(self.address):
            raise RuntimeError("bluetooth_address_invalid")
        if not 1 <= self.channel <= 30:
            raise RuntimeError("bluetooth_channel_invalid")

        if self._socket_factory is not None:
            handle = self._socket_factory()
        else:
            required = ("AF_BLUETOOTH", "BTPROTO_RFCOMM")
            if not all(hasattr(socket, name) for name in required):
                raise RuntimeError("bluetooth_rfcomm_unsupported")
            handle = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)

        handle.settimeout(self.timeout_s)
        handle.connect((self.address, self.channel))
        self._socket = handle
        return handle

    def _read_matching_response(self, handle, request_id: str) -> MegaResponse:
        deadline = time.monotonic() + self.timeout_s
        while time.monotonic() < deadline:
            newline = self._receive_buffer.find(b"\n")
            if newline >= 0:
                line = bytes(self._receive_buffer[:newline]).strip()
                del self._receive_buffer[: newline + 1]
                if not line:
                    continue
                try:
                    response = decode_response(line)
                except Exception:
                    # Boot/watchdog events are valid NDJSON but not MegaResponse.
                    continue
                if response.id == request_id:
                    return response
                continue

            chunk = handle.recv(512)
            if not chunk:
                raise ConnectionError("bluetooth_rfcomm_disconnected")
            self._receive_buffer.extend(chunk)
            if len(self._receive_buffer) > 65536:
                raise RuntimeError("bluetooth_response_too_large")

        raise TimeoutError("bluetooth_response_timeout")

    def _close_socket(self) -> None:
        handle = self._socket
        self._socket = None
        self._receive_buffer.clear()
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass
