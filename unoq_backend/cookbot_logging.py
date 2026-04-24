import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import CommandLogEntry


class CookBotJsonLogger:
    def __init__(self, path: Path):
        self.path = path

    def event(self, source: str, event: str, **fields: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "event": event,
            **fields,
        }
        record = {key: value for key, value in record.items() if value is not None}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def tail(self, limit: int = 100) -> list[CommandLogEntry]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
        entries: list[CommandLogEntry] = []
        for line in lines:
            try:
                data = json.loads(line)
                entries.append(CommandLogEntry.model_validate(data))
            except Exception:
                continue
        return entries
