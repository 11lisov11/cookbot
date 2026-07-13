import argparse
import asyncio
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unoq_backend.vendor_gcode import VendorControllerEmulator


def execute_once(line: str, *, as_json: bool = False) -> int:
    emulator = VendorControllerEmulator()
    try:
        result = emulator.execute(line)
    except ValueError as exc:
        if as_json:
            print(json.dumps({"ok": False, "error": str(exc)}))
        else:
            print(f"error {exc}")
        return 2

    if as_json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "command": result.command.model_dump(),
                    "coordinates": result.state.coordinates,
                    "feed_mm_s": result.state.feed_mm_s,
                    "response": result.response_line.rstrip("\n"),
                }
            )
        )
    else:
        print(result.response_line, end="")
    return 0


def run_stdio() -> int:
    emulator = VendorControllerEmulator()
    for line in sys.stdin:
        try:
            print(emulator.execute(line).response_line, end="", flush=True)
        except ValueError as exc:
            print(f"error {exc}", flush=True)
    return 0


async def handle_tcp_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    emulator = VendorControllerEmulator()
    buffer = ""
    try:
        while chunk := await reader.read(256):
            for character in chunk.decode("ascii", errors="strict"):
                if character not in "\r\n":
                    if len(buffer) >= 256:
                        writer.write(b"error command_too_long\n")
                        await writer.drain()
                        buffer = ""
                    else:
                        buffer += character
                    continue
                if not buffer.strip():
                    buffer = ""
                    continue
                try:
                    response = emulator.execute(buffer).response_line
                except ValueError as exc:
                    response = f"error {exc}\n"
                writer.write(response.encode("ascii"))
                await writer.drain()
                buffer = ""
    finally:
        writer.close()
        await writer.wait_closed()


async def run_tcp(host: str, port: int) -> None:
    server = await asyncio.start_server(handle_tcp_client, host, port)
    addresses = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"AXIS4UI behavioral emulator listening on {addresses}", flush=True)
    async with server:
        await server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safe AXIS4UI protocol emulator; never opens a serial port."
    )
    parser.add_argument("--once", help="Execute one vendor G-code line and exit.")
    parser.add_argument("--json", action="store_true", help="Use JSON output with --once.")
    parser.add_argument("--tcp", action="store_true", help="Serve the protocol over TCP.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8768)
    args = parser.parse_args()

    if args.once is not None:
        return execute_once(args.once, as_json=args.json)
    if args.tcp:
        asyncio.run(run_tcp(args.host, args.port))
        return 0
    return run_stdio()


if __name__ == "__main__":
    raise SystemExit(main())
