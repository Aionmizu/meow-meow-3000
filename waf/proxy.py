from __future__ import annotations

import posixpath
import urllib.parse
from typing import Dict, Tuple, Any

import httpx
from flask import Flask, request, Response, make_response

from .config import settings
from .logger import append_log, new_request_id, utc_now_iso, time_ms
from .scoring import compute_score, severity_from_score


def _build_target_url(incoming_path: str, incoming_query: str) -> str:
    base = settings.backend_base_url
    parts = urllib.parse.urlparse(base)
    base_path = parts.path or "/"
    # join path safely (avoid resetting to root when incoming_path starts with '/')
    joined_path = posixpath.join(base_path.rstrip("/"), incoming_path.lstrip("/"))
    new_parts = parts._replace(path=joined_path, query=incoming_query)
    return urllib.parse.urlunparse(new_parts)


def _collect_text_for_analysis() -> str:
    # path + query + body + selected headers
    path = request.path or "/"
    qs = request.query_string.decode("utf-8", errors="ignore")
    try:
        body_text = request.get_data(cache=True, as_text=True)
    except Exception:
        body_text = ""
    ua = request.headers.get("User-Agent", "")
    referer = request.headers.get("Referer", "")
    cookie = request.headers.get("Cookie", "")
    return "\n".join([path, qs, body_text or "", ua, referer, cookie])


def _filtered_request_headers(target_url: str) -> Dict[str, str]:
    # Filter hop-by-hop headers and set Host of backend
    hop_by_hop = {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
    headers: Dict[str, str] = {}
    for k, v in request.headers.items():
        lk = k.lower()
        if lk in hop_by_hop:
            continue
        if lk == "host":
            continue
        headers[k] = v
    # set Host to backend host
    host = urllib.parse.urlparse(target_url).netloc
    headers["Host"] = host
    # Add X-Forwarded-* headers
    headers.setdefault("X-Forwarded-For", request.remote_addr or "unknown")
    headers.setdefault("X-Forwarded-Proto", request.scheme)
    headers.setdefault("X-Forwarded-Host", request.host)
    return headers


def _filtered_response(resp: httpx.Response, waf_headers: Dict[str, str]) -> Response:
    # Build Flask response with filtered headers
    excluded = {"content-encoding", "transfer-encoding", "connection"}
    response = make_response(resp.content, resp.status_code)
    for k, v in resp.headers.items():
        if k.lower() in excluded:
            continue
        response.headers[k] = v
    for k, v in waf_headers.items():
        response.headers[k] = v
    return response


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/healthz", methods=["GET"])  # simple health endpoint
    def healthz():
        return {"status": "ok", "mode": settings.mode}

    @app.route("/", defaults={"path": ""}, methods=[
        "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"
    ])
    @app.route("/<path:path>", methods=[
        "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"
    ])
    def proxy(path: str):  # type: ignore[override]
        started = time_ms()
        rid = new_request_id()
        source_ip = request.remote_addr or "unknown"
        method = request.method

        # Allow mode override via query param for demo if enabled
        mode = settings.mode
        if settings.allow_query_mode_switch:
            qmode = request.args.get("waf_mode")
            if qmode and qmode.upper() in {"IDS", "IPS"}:
                mode = qmode.upper()

        # Compute score (robuste: aucune exception ne doit casser la requête)
        try:
            text = _collect_text_for_analysis()
            score, matched_rules, flags = compute_score(text)
        except Exception as e:
            # En cas d'erreur d'analyse, on marque score=0 mais on continue et on loguera l'erreur
            score, matched_rules, flags = 0, [], {"analysis_error": True}
        severity = severity_from_score(score)

        # Action resolution
        action = "ALLOW"
        if mode == "IPS" and score >= settings.threshold_block:
            action = "BLOCK"

        duration_ms = None
        status_code = 403 if action == "BLOCK" else None
        target_url = _build_target_url(path, request.query_string.decode("utf-8", errors="ignore"))
        waf_hdrs = {
            "X-WAF-Score": str(score),
            "X-WAF-Severity": severity,
            "X-WAF-Action": action,
            "X-Request-ID": rid,
        }

        if action == "BLOCK":
            duration_ms = time_ms() - started
            append_log({
                "timestamp": utc_now_iso(),
                "request_id": rid,
                "source_ip": source_ip,
                "method": method,
                "url": request.url,
                "backend_url": target_url,
                "score": score,
                "severity": severity,
                "matched_rules": matched_rules,
                "flags": flags,
                "action": action,
                "status": 403,
                "user_agent": request.headers.get("User-Agent", ""),
                "response_time_ms": duration_ms,
            })
            body = {
                "error": "Blocked by WAF",
                "action": action,
                "score": score,
                "severity": severity,
                "rules": matched_rules,
                "request_id": rid,
            }
            resp = make_response(body, 403)
            for k, v in waf_hdrs.items():
                resp.headers[k] = v
            return resp

        # Forward to backend
        try:
            req_body = request.get_data(cache=True)  # bytes
            headers = _filtered_request_headers(target_url)
            with httpx.Client(follow_redirects=False, timeout=15.0, verify=False) as client:
                upstream_resp = client.request(method, target_url, headers=headers, content=req_body)
        except Exception as e:  # Capture toute erreur (httpx, encodage, etc.)
            duration_ms = time_ms() - started
            append_log({
                "timestamp": utc_now_iso(),
                "request_id": rid,
                "source_ip": source_ip,
                "method": method,
                "url": request.url,
                "backend_url": target_url,
                "score": score,
                "severity": severity,
                "matched_rules": matched_rules,
                "flags": {**(flags or {}), "proxy_error": True},
                "action": "ERROR",
                "status": 502,
                "error": str(e),
                "user_agent": request.headers.get("User-Agent", ""),
                "response_time_ms": duration_ms,
            })
            resp = make_response({"error": "Bad Gateway", "details": str(e)}, 502)
            for k, v in waf_hdrs.items():
                resp.headers[k] = v
            return resp

        duration_ms = time_ms() - started
        response = _filtered_response(upstream_resp, waf_hdrs)

        # Log event
        append_log({
            "timestamp": utc_now_iso(),
            "request_id": rid,
            "source_ip": source_ip,
            "method": method,
            "url": request.url,
            "backend_url": target_url,
            "score": score,
            "severity": severity,
            "matched_rules": matched_rules,
            "flags": flags,
            "action": action,
            "status": upstream_resp.status_code,
            "user_agent": request.headers.get("User-Agent", ""),
            "response_time_ms": duration_ms,
        })
        return response

    return app
