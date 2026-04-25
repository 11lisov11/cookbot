import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dist" / "release"
MANIFEST_NAME = "COOKBOT_RELEASE_MANIFEST.json"
LATEST_NAME = "latest_release_path.txt"


def main() -> int:
    parser = argparse.ArgumentParser(prog="cookbot-release-tooling")
    subcommands = parser.add_subparsers(dest="command", required=True)

    plan = subcommands.add_parser("plan")
    plan.add_argument("--json", action="store_true")
    plan.set_defaults(fn=cmd_plan)

    build = subcommands.add_parser("build")
    build.add_argument("--output", default=str(DEFAULT_OUTPUT))
    build.add_argument("--version", default=None)
    build.add_argument("--skip-generated", action="store_true")
    build.add_argument("--json", action="store_true")
    build.set_defaults(fn=cmd_build)

    validate = subcommands.add_parser("validate")
    validate.add_argument("bundle", nargs="?")
    validate.add_argument("--output", default=str(DEFAULT_OUTPUT))
    validate.add_argument("--latest", action="store_true")
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(fn=cmd_validate)

    args = parser.parse_args()
    return int(args.fn(args))


def cmd_plan(args: argparse.Namespace) -> int:
    plan = build_release_plan(skip_generated=False, version=None)
    _emit(plan, args.json)
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    plan = build_release_plan(skip_generated=args.skip_generated, version=args.version)
    zip_name = f"cookbot-{plan['version']}-{plan['git_commit']}.zip"
    bundle_path = output / zip_name

    manifest = {
        "project": "CookBot",
        "manifest_version": "1",
        "version": plan["version"],
        "git_commit": plan["git_commit"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "real_motion_locked": True,
        "ready_for_real_motion": False,
        "generated_artifacts": plan["generated_artifacts"],
        "files": [],
    }

    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in plan["files"]:
            source = ROOT / item["path"]
            data = source.read_bytes()
            archive.writestr(item["path"], data)
            manifest["files"].append(
                {
                    "path": item["path"],
                    "category": item["category"],
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        archive.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2, sort_keys=True))

    bundle_sha256 = _sha256_file(bundle_path)
    latest = output / LATEST_NAME
    latest.write_text(str(bundle_path.resolve()), encoding="utf-8")
    result = {
        "ok": True,
        "bundle": str(bundle_path),
        "bundle_sha256": bundle_sha256,
        "file_count": len(manifest["files"]),
        "version": manifest["version"],
        "git_commit": manifest["git_commit"],
        "real_motion_locked": manifest["real_motion_locked"],
        "ready_for_real_motion": manifest["ready_for_real_motion"],
        "generated_artifacts": manifest["generated_artifacts"],
    }
    _emit(result, args.json)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    bundle = _resolve_bundle(args)
    if not bundle:
        return _fail("release_bundle_required", args.json, 2)
    if not bundle.exists():
        return _fail(f"release_bundle_not_found:{bundle}", args.json, 2)
    try:
        result = validate_bundle(bundle)
    except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
        return _fail(f"release_bundle_invalid:{exc}", args.json, 3)
    _emit(result, args.json)
    return 0 if result["ok"] else 4


def build_release_plan(skip_generated: bool, version: str | None) -> dict[str, Any]:
    tracked_files = [{"path": path, "category": "source"} for path in _git_files()]
    generated = [] if skip_generated else _generated_artifacts()
    files = _dedupe_files([*tracked_files, *generated])
    return {
        "project": "CookBot",
        "version": version or _package_version(),
        "git_commit": _git_commit(),
        "real_motion_locked": True,
        "ready_for_real_motion": False,
        "files": files,
        "file_count": len(files),
        "generated_artifacts": _generated_status(),
    }


def validate_bundle(bundle_path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(bundle_path) as archive:
        manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
        failures: list[str] = []
        for item in manifest["files"]:
            try:
                data = archive.read(item["path"])
            except KeyError:
                failures.append(f"missing:{item['path']}")
                continue
            actual = hashlib.sha256(data).hexdigest()
            if actual != item["sha256"]:
                failures.append(f"sha256_mismatch:{item['path']}")
            if len(data) != item["size"]:
                failures.append(f"size_mismatch:{item['path']}")
        if not manifest.get("real_motion_locked") or manifest.get("ready_for_real_motion"):
            failures.append("release_motion_gate_invalid")
    return {
        "ok": not failures,
        "bundle": str(bundle_path),
        "bundle_sha256": _sha256_file(bundle_path),
        "file_count": len(manifest.get("files", [])),
        "version": manifest.get("version"),
        "git_commit": manifest.get("git_commit"),
        "real_motion_locked": manifest.get("real_motion_locked"),
        "ready_for_real_motion": manifest.get("ready_for_real_motion"),
        "failures": failures,
    }


def _git_files() -> list[str]:
    output = _run_capture(["git", "ls-files"], check=True)
    files = [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]
    return [path for path in files if _include_source_path(path)]


def _include_source_path(path: str) -> bool:
    excluded_prefixes = (
        ".git/",
        ".pio/",
        "dist/",
        "web/dist/",
        "web/node_modules/",
        "logs/",
    )
    return not path.startswith(excluded_prefixes)


def _generated_artifacts() -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    generated_roots = [
        ("web/dist", "web_dist"),
    ]
    for root, category in generated_roots:
        base = ROOT / root
        if base.exists():
            for path in sorted(base.rglob("*")):
                if path.is_file():
                    artifacts.append({"path": _relative(path), "category": category})

    firmware_files = [
        ".pio/build/cookbot_mega2560/firmware.hex",
        ".pio/build/cookbot_mega2560/firmware.elf",
        ".pio/build/cookbot_mega2560_bench/firmware.hex",
        ".pio/build/cookbot_mega2560_bench/firmware.elf",
    ]
    for rel in firmware_files:
        if (ROOT / rel).exists():
            artifacts.append({"path": rel, "category": "mega_firmware_build"})
    return artifacts


def _generated_status() -> dict[str, bool]:
    return {
        "web_dist": (ROOT / "web" / "dist" / "index.html").exists(),
        "platformio_locked_hex": (ROOT / ".pio" / "build" / "cookbot_mega2560" / "firmware.hex").exists(),
        "platformio_bench_hex": (ROOT / ".pio" / "build" / "cookbot_mega2560_bench" / "firmware.hex").exists(),
    }


def _dedupe_files(files: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for item in files:
        path = item["path"].replace("\\", "/")
        source = ROOT / path
        if path in seen or not source.is_file():
            continue
        seen.add(path)
        result.append({"path": path, "category": item["category"]})
    return sorted(result, key=lambda item: item["path"])


def _resolve_bundle(args: argparse.Namespace) -> Path | None:
    if args.latest:
        latest = Path(args.output) / LATEST_NAME
        if not latest.exists():
            return None
        return Path(latest.read_text(encoding="utf-8").strip())
    if args.bundle:
        return Path(args.bundle)
    return None


def _package_version() -> str:
    package = ROOT / "web" / "package.json"
    if package.exists():
        try:
            return json.loads(package.read_text(encoding="utf-8")).get("version", "0.1.0")
        except json.JSONDecodeError:
            return "0.1.0"
    return "0.1.0"


def _git_commit() -> str:
    return _run_capture(["git", "rev-parse", "--short", "HEAD"], check=False).strip() or "unknown"


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_capture(command: list[str], check: bool) -> str:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=check)
    return result.stdout


def _emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        if key == "manifest":
            print(f"{key}: {len(value.get('files', []))} files")
        else:
            print(f"{key}: {value}")


def _fail(message: str, as_json: bool, code: int) -> int:
    payload = {"ok": False, "error": message}
    _emit(payload, as_json)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
