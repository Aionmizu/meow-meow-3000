from __future__ import annotations

import re
import urllib.parse
from typing import List, Tuple, Dict

# --- Normalization helpers ---

def _safe_unquote_plus(s: str) -> str:
    """Décoder seulement les séquences %xx valides et traiter '+' comme espace.
    Ne lève jamais d'exception, remplace les séquences invalides par elles‑mêmes.
    """
    if s is None:
        return ""
    # Remplacer '+' par espace pour mimer unquote_plus
    s2 = s.replace("+", " ")
    # Remplacer uniquement les %xx valides
    def _repl(m: re.Match[str]) -> str:
        try:
            return bytes.fromhex(m.group(0)[1:]).decode("utf-8", errors="replace")
        except Exception:
            return m.group(0)
    return re.sub(r"%[0-9a-fA-F]{2}", _repl, s2)


def url_decode_all(s: str) -> Tuple[str, Dict[str, bool]]:
    """URL-decode de manière robuste; détecte le double décodage.
    Ne plante pas sur des encodages invalides (ex: "%E", "%ZZ").
    Retourne (decoded, flags) avec flags = {"double_decoded": bool, "had_encoding": bool}
    """
    if not s:
        return "", {"double_decoded": False, "had_encoding": False}
    had_encoding = ("%" in s) or ("+" in s)
    try:
        once = urllib.parse.unquote_plus(s)
    except Exception:
        once = _safe_unquote_plus(s)
    try:
        twice = urllib.parse.unquote_plus(once)
    except Exception:
        twice = _safe_unquote_plus(once)
    return twice, {"double_decoded": twice != once, "had_encoding": had_encoding}


def normalize_payload(s: str) -> Tuple[str, Dict[str, bool]]:
    """Apply normalization: URL decode, lowercase, remove comments, collapse spaces,
    replace encoded control chars.
    Returns (normalized_text, flags)
    """
    decoded, flags = url_decode_all(s)
    s2 = decoded.lower()
    # Remove C-style comments often used for bypass: /**/
    s2 = re.sub(r"/\*+\*/", " ", s2)
    # Replace encoded control chars remnants
    s2 = s2.replace("%0a", " ").replace("%0d", " ").replace("%09", " ")
    # Collapse multiple spaces/tabs
    s2 = re.sub(r"\s+", " ", s2)
    return s2.strip(), flags


# --- Signature rules ---
# Each pattern is a tuple: (name, compiled_regex, score)

SQLI_PATTERNS: List[Tuple[str, re.Pattern, int]] = [
    ("SQLI_OR_1EQ1", re.compile(r"(['\"]\s*or\s*1\s*=\s*1)"), 5),
    # Reinforced: UNION SELECT now worth 6 points
    ("SQLI_UNION_SELECT", re.compile(r"\bunion\s+select\b"), 6),
    ("SQLI_SLEEP_FN", re.compile(r"\bsleep\s*\("), 4),
    ("SQLI_DROP_TABLE", re.compile(r";\s*drop\s+table"), 6),
    ("SQLI_HEX_ENC_OR", re.compile(r"%27\s*or\s*1%3d1"), 4),
    # New: bare OR 1=1 without preceding quote
    ("SQLI_BARE_OR_1EQ1", re.compile(r"\bor\s*1\s*=\s*1\b"), 4),
    # New: comment dashes pattern often used in SQLi
    ("SQLI_COMMENT_DASH", re.compile(r"--\s"), 2),
    # New: stacked queries using '; select'
    ("SQLI_STACKED_QUERIES", re.compile(r";\s*select\b"), 4),
]

XSS_PATTERNS: List[Tuple[str, re.Pattern, int]] = [
    ("XSS_SCRIPT_TAG", re.compile(r"<\s*script\b"), 5),
    ("XSS_ATTR_ONERROR", re.compile(r"onerror\s*="), 4),
    ("XSS_JS_PROTO", re.compile(r"javascript:\s*"), 4),
    ("XSS_QUOTE_BREAK_SCRIPT", re.compile(r"\"\s*>\s*<\s*script"), 5),
    ("XSS_ENC_SCRIPT", re.compile(r"%3c\s*script\s*%3e"), 4),
    # New: image onerror handler
    ("XSS_IMG_ONERROR", re.compile(r"<img[^>]+onerror="), 4),
]

ENCODING_PATTERNS: List[Tuple[str, re.Pattern, int]] = [
    ("ENC_PERCENT_HEAVY", re.compile(r"%[0-9a-f]{2}(%[0-9a-f]{2}){2,}"), 3),
]

# Other generic attack patterns
OTHER_PATTERNS: List[Tuple[str, re.Pattern, int]] = [
    ("PATH_TRAVERSAL", re.compile(r"\.\./"), 3),
    ("LFI_WRAPPER", re.compile(r"php://|data://"), 4),
    ("CMD_INJECTION", re.compile(r";\s*(id|whoami|cat)\b"), 4),
]

ALL_PATTERNS = SQLI_PATTERNS + XSS_PATTERNS + ENCODING_PATTERNS + OTHER_PATTERNS


def match_rules(text: str) -> List[Tuple[str, int]]:
    """Return list of (rule_name, score) matched in text."""
    matches: List[Tuple[str, int]] = []
    for name, pattern, score in ALL_PATTERNS:
        if pattern.search(text):
            matches.append((name, score))
    return matches
