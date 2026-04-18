import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.isoformat(timespec="milliseconds").replace("+00:00", "Z")

def invalid_log_path(log_file: str) -> Path:
    return Path(log_file).expanduser().with_name("events.invalid.jsonl")

def append_jsonl(path: str | Path, record: dict[str, Any]) -> None:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

def log_verified_event(log_file: str, event: str, payload: dict[str, Any]) -> None:
    append_jsonl(
        log_file,
        {
            "received_at": utc_now_iso(),
            "event": event,
            "signature_valid": True,
            "payload": payload,
        },
    )

def log_invalid_attempt(log_file: str, reason: str, headers: dict[str, str]) -> None:
    append_jsonl(
        invalid_log_path(log_file),
        {"received_at": utc_now_iso(), "reason": reason, "headers": headers},
    )
