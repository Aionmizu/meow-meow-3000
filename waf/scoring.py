from __future__ import annotations

from typing import Dict, List, Tuple

from .rules import normalize_payload, match_rules


def compute_score(raw_text: str) -> Tuple[int, List[str], Dict[str, bool]]:
    """Normalize input, match signatures, and compute a score.
    Returns: (score, matched_rule_names, flags)
    flags contains keys like: had_encoding, double_decoded
    """
    normalized, flags = normalize_payload(raw_text or "")
    matches = match_rules(normalized)
    score = sum(s for _, s in matches)

    # Additional scoring based on encoding flags
    if flags.get("had_encoding"):
        score += 3
    if flags.get("double_decoded"):
        score += 4

    return score, [name for name, _ in matches], flags


def severity_from_score(score: int) -> str:
    if score <= 0:
        return "none"
    if score < 5:
        return "low"
    if score < 9:
        return "high"
    return "critical"
