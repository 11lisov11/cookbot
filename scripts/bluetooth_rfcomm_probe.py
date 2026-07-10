import argparse
import asyncio
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from unoq_backend.transports import BluetoothRfcommMegaTransport


async def probe(address: str, channel: int, timeout: float) -> dict:
    transport = BluetoothRfcommMegaTransport(address, channel, timeout)
    try:
        responses = {}
        for command in ("hello", "ping", "get_firmware_status", "self_test", "read_inputs"):
            response = await transport.send(command)
            responses[command] = response.model_dump(mode="json")
            if not response.ok:
                raise RuntimeError(response.error or f"{command}_failed")
        return {"ok": True, "address": address.upper(), "channel": channel, "responses": responses}
    finally:
        transport.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe CookBot Mega over Bluetooth RFCOMM")
    parser.add_argument("--address", required=True)
    parser.add_argument("--channel", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "address": args.address, "channel": args.channel}))
        return 0
    try:
        result = asyncio.run(probe(args.address, args.channel, args.timeout))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
