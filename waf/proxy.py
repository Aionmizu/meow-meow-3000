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
    """Construire l'URL cible en évitant les doubles préfixes.
    Si le backend est servi sous une base non racine (ex: /DVWA) et que le
    client appelle déjà un chemin qui commence par cette base, on n'ajoute pas
    le préfixe une deuxième fois.
    """
    base = settings.backend_base_url
    parts = urllib.parse.urlparse(base)
    base_path = parts.path or "/"

    # Normaliser
    inc_path = incoming_path or "/"

    # Si le chemin entrant commence déjà par la base backend, ne pas doubler
    if base_path != "/":
        bp = base_path.rstrip("/")
        if inc_path.startswith(bp + "/") or inc_path == bp:
            joined_path = inc_path
        else:
            joined_path = posixpath.join(bp, inc_path.lstrip("/"))
    else:
        joined_path = "/" + inc_path.lstrip("/")

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
    # Build Flask response with filtered headers (strip hop-by-hop and content-length)
    excluded = {
        "content-length",
        "content-encoding",
        "transfer-encoding",
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "upgrade",
    }
    # On peut être amené à réécrire le corps (HTML) pour garder le client derrière le WAF.
    will_rewrite_body = False
    content_type = resp.headers.get("Content-Type", "")
    if "text/html" in content_type or "text/css" in content_type:
        will_rewrite_body = True

    body_bytes = resp.content
    if will_rewrite_body:
        try:
            backend_parts = urllib.parse.urlparse(settings.backend_base_url)
            backend_origin = f"{backend_parts.scheme}://{backend_parts.netloc}"
            waf_origin = f"{request.scheme}://{request.host}"
            txt = resp.text  # utilise l'encodage détecté par httpx
            # Réécrit les URLs absolues et schéma-relatives vers le backend
            txt = txt.replace(backend_origin, waf_origin)
            txt = txt.replace(f"//{backend_parts.netloc}", f"//{request.host}")
            # Ré-encode en conservant l'encodage amont si possible
            enc = resp.encoding or "utf-8"
            body_bytes = txt.encode(enc, errors="replace")
        except Exception:
            # En cas de problème, on renvoie le corps original
            body_bytes = resp.content

    response = make_response(body_bytes, resp.status_code)
    # Copie des en-têtes retour amont (sauf hop-by-hop)
    for k, v in resp.headers.items():
        lk = k.lower()
        if lk in excluded:
            continue
        # Réécriture éventuelle du Domain des cookies pour rester sur l'hôte du WAF
        if lk == "set-cookie":
            try:
                backend_parts = urllib.parse.urlparse(settings.backend_base_url)
                backend_host = backend_parts.hostname or ""
                waf_host_only = request.host.split(":")[0]
                if backend_host and backend_host in v:
                    v = v.replace(f"Domain={backend_host}", f"Domain={waf_host_only}")
            except Exception:
                pass
        # Préserver les multiples Set-Cookie en utilisant add()
        if lk == "set-cookie":
            response.headers.add(k, v)
        else:
            response.headers[k] = v

    # Réécriture éventuelle de Location pour éviter de sortir du WAF
    loc = resp.headers.get("Location")
    if loc:
        try:
            backend_parts = urllib.parse.urlparse(settings.backend_base_url)
            target = urllib.parse.urlparse(loc)
            # Si Location est absolue et pointe vers l'hôte backend (avec ou sans port par défaut), on réécrit
            if target.scheme and target.netloc:
                backend_host = backend_parts.hostname or ""
                backend_netlocs = {backend_parts.netloc, backend_host}
                # Ajouter netloc avec port par défaut selon le schéma
                if backend_parts.scheme in ("http", "https") and backend_host:
                    default_port = 80 if backend_parts.scheme == "http" else 443
                    backend_netlocs.add(f"{backend_host}:{default_port}")
                if target.netloc in backend_netlocs:
                    # Conserver le chemin/query de la Location, remplacer schéma/hôte par ceux du WAF
                    new_loc = urllib.parse.urlunparse(
                        (
                            request.scheme,
                            request.host,  # inclut le port du WAF
                            target.path,
                            target.params,
                            target.query,
                            target.fragment,
                        )
                    )
                    response.headers["Location"] = new_loc
        except Exception:
            # En cas de doute, on laisse Location telle quelle
            pass

    # Ajuster Content-Length si nous avons réécrit le corps (sinon laisser Werkzeug calculer)
    if will_rewrite_body:
        try:
            response.headers["Content-Length"] = str(len(body_bytes))
        except Exception:
            pass

    # Ajouter les en-têtes WAF
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


def create_app_with_error_handler() -> Flask:
    """Same as create_app(), but with a global error handler to guarantee logging.
    Kept separate for clarity; prefer using this in runners.
    """
    app = create_app()

    @app.errorhandler(Exception)
    def _handle_unexpected_error(e: Exception):  # type: ignore[override]
        # Try to salvage as much context as possible and always log the event
        rid = new_request_id()
        try:
            text = _collect_text_for_analysis()
            score, matched_rules, flags = compute_score(text)
        except Exception:
            score, matched_rules, flags = 0, [], {"analysis_error": True}
        severity = severity_from_score(score)
        waf_hdrs = {
            "X-WAF-Score": str(score),
            "X-WAF-Severity": severity,
            "X-WAF-Action": "ERROR",
            "X-Request-ID": rid,
        }
        try:
            target_url = _build_target_url(request.path or "/", request.query_string.decode("utf-8", errors="ignore"))
        except Exception:
            target_url = ""
        append_log({
            "timestamp": utc_now_iso(),
            "request_id": rid,
            "source_ip": getattr(request, 'remote_addr', None) or "unknown",
            "method": getattr(request, 'method', None) or "UNKNOWN",
            "url": getattr(request, 'url', None) or "",
            "backend_url": target_url,
            "score": score,
            "severity": severity,
            "matched_rules": matched_rules,
            "flags": {**(flags or {}), "unhandled_exception": True},
            "action": "ERROR",
            "status": 500,
            "user_agent": request.headers.get("User-Agent", "") if hasattr(request, 'headers') else "",
            "response_time_ms": None,
        })
        resp = make_response({
            "error": "Internal Server Error",
            "request_id": rid,
        }, 500)
        for k, v in waf_hdrs.items():
            resp.headers[k] = v
        return resp

    return app
