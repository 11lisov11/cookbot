import base64
import itertools
import subprocess
import tempfile
from pathlib import Path

from .models import CameraSnapshot


MOCK_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
<rect width="640" height="360" fill="#111315"/>
<rect x="36" y="38" width="568" height="284" rx="10" fill="#1d2328" stroke="#44515a"/>
<circle cx="320" cy="180" r="74" fill="#2f7d63"/>
<path d="M250 202c42-56 98-56 140 0" fill="none" stroke="#e9c46a" stroke-width="18" stroke-linecap="round"/>
<text x="320" y="318" fill="#e8ecef" font-family="Arial" font-size="24" text-anchor="middle">CookBot mock camera</text>
</svg>"""


class MockCamera:
    def snapshot(self) -> CameraSnapshot:
        raw = MOCK_SVG.encode("utf-8")
        encoded = base64.b64encode(raw).decode("ascii")
        return CameraSnapshot(
            mode="mock",
            media_type="image/svg+xml",
            data_base64=encoded,
            data_url=f"data:image/svg+xml;base64,{encoded}",
        )

    def multipart_frame(self) -> bytes:
        raw = MOCK_SVG.encode("utf-8")
        return (
            b"--frame\r\n"
            b"Content-Type: image/svg+xml\r\n"
            + f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii")
            + raw
            + b"\r\n"
        )

    def stream_frames(self, frame_count: int | None = None):
        iterator = range(frame_count) if frame_count is not None else itertools.count()
        for _ in iterator:
            yield self.multipart_frame()


class LibcameraStillCamera:
    def snapshot(self) -> CameraSnapshot:
        with tempfile.TemporaryDirectory(prefix="cookbot-camera-") as tmp:
            output = Path(tmp) / "snapshot.jpg"
            command = [
                "libcamera-still",
                "-n",
                "--timeout",
                "1000",
                "--width",
                "640",
                "--height",
                "360",
                "-o",
                str(output),
            ]
            try:
                subprocess.run(command, check=True, capture_output=True, timeout=5)
            except (FileNotFoundError, subprocess.SubprocessError) as exc:
                raise ValueError(f"camera_capture_failed:{exc}") from exc
            raw = output.read_bytes()
        encoded = base64.b64encode(raw).decode("ascii")
        return CameraSnapshot(
            mode="libcamera",
            media_type="image/jpeg",
            data_base64=encoded,
            data_url=f"data:image/jpeg;base64,{encoded}",
        )
