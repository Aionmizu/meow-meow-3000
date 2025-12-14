from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request

from .config import settings


def read_logs(limit: int | None = None) -> List[Dict[str, Any]]:
    path = settings.logs_file
    if not os.path.exists(path):
        return []
    entries: List[Dict[str, Any]] = []
    # Tolérance maximale aux caractères invalides pour ne jamais planter l'API/dashboard
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    if limit:
        return entries[-limit:]
    return entries


def create_dashboard_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.route("/")
    def root():
        return render_template("dashboard.html")

    @app.route("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    @app.get("/api/logs")
    def api_logs():
        limit = request.args.get("limit", type=int) or 200
        severity = (request.args.get("severity") or "").lower().strip()
        rule = (request.args.get("rule") or "").strip()
        action = (request.args.get("action") or "").upper().strip()

        data = read_logs(limit=None)
        if severity:
            data = [e for e in data if (str(e.get("severity", "")).lower() == severity)]
        if rule:
            data = [e for e in data if rule in (e.get("matched_rules") or [])]
        if action:
            data = [e for e in data if str(e.get("action", "")).upper() == action]
        if limit:
            data = data[-limit:]
        return jsonify({"items": data, "count": len(data)})

    @app.post("/api/logs/clear")
    def api_logs_clear():
        path = settings.logs_file
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8"):
            pass
        return jsonify({"status": "ok"})

    return app
