from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

try:
    import orjson  # type: ignore
except Exception:  # pragma: no cover - optional
    orjson = None  # type: ignore

from .config import settings


def _json_dumps(obj: Any) -> str:
    if orjson is not None:
        return orjson.dumps(obj).decode("utf-8")
    return json.dumps(obj, ensure_ascii=False)


def ensure_data_dir():
    os.makedirs(os.path.dirname(settings.logs_file), exist_ok=True)


def new_request_id() -> str:
    return uuid.uuid4().hex


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_log(event: Dict[str, Any]) -> None:
    try:
        ensure_data_dir()
        line = _json_dumps(event)
        with open(settings.logs_file, "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")
    except Exception:
        # En dernier recours, on ignore l'erreur d'écriture pour ne pas casser la réponse WAF
        pass


def time_ms() -> int:
    return int(time.time() * 1000)
