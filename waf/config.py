from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


# Base directory of the project/package (more stable than CWD under systemd)
_PKG_DIR = Path(__file__).resolve().parent
_BASE_DIR = _PKG_DIR.parent  # project root when running from repo or install dir


@dataclass(frozen=True)
class Settings:
    # Backend DVWA base URL (Kali's Apache)
    backend_base_url: str = os.getenv("WAF_BACKEND", "http://127.0.0.1/dvwa")

    # Mode: IDS (log-only) or IPS (block when score > threshold)
    mode: str = os.getenv("WAF_MODE", "IPS").upper()  # "IDS" or "IPS"

    # Scoring thresholds
    threshold_ids: int = int(os.getenv("WAF_THRESHOLD_IDS", "5"))
    threshold_block: int = int(os.getenv("WAF_THRESHOLD_BLOCK", "9"))

    # Listen address/port for the proxy and dashboard
    host: str = os.getenv("WAF_LISTEN_HOST", "0.0.0.0")
    port: int = int(os.getenv("WAF_LISTEN_PORT", "8080"))

    dashboard_host: str = os.getenv("WAF_DASHBOARD_HOST", "0.0.0.0")
    dashboard_port: int = int(os.getenv("WAF_DASHBOARD_PORT", "5001"))

    # Paths
    # Defaults to a path relative to the install/project directory, not the current working dir
    data_dir: str = os.getenv("WAF_DATA_DIR", str(_BASE_DIR / "data"))
    logs_file: str = os.getenv("WAF_LOGS_FILE", os.path.join(data_dir, "logs.json"))

    # Feature toggles
    allow_query_mode_switch: bool = os.getenv("WAF_ALLOW_QUERY_MODE_SWITCH", "1") == "1"


settings = Settings()
