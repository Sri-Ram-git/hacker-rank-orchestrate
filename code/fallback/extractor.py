import re
from .mappings import ISSUE_KEYWORDS, PART_KEYWORDS, CLAIM_TEMPLATES
from models.schemas import constrain_issue_type, constrain_object_part


CUSTOMER_PREFIXES = ["customer:", "cliente:", "cliente", "customer"]
AGENT_PREFIXES = ["agent:", "support:", "soporte:", "agent"]


def _all_customer_statements(text: str) -> str:
    segments = [s.strip() for s in text.split("|")]
    customer_parts = []
    for seg in segments:
        lower = seg.lower()
        is_customer = any(lower.startswith(p) for p in CUSTOMER_PREFIXES)
        if is_customer:
            for p in CUSTOMER_PREFIXES:
                if lower.startswith(p):
                    seg = seg[len(p):].strip()
                    break
            customer_parts.append(seg)
    combined = " ".join(customer_parts)
    if combined:
        return combined
    return text


def _last_customer_statement(text: str) -> str:
    segments = [s.strip() for s in text.split("|")]
    last_customer = ""
    for seg in segments:
        lower = seg.lower()
        is_customer = any(lower.startswith(p) for p in CUSTOMER_PREFIXES)
        if is_customer:
            for p in CUSTOMER_PREFIXES:
                if lower.startswith(p):
                    seg = seg[len(p):].strip()
                    break
            last_customer = seg
    if last_customer:
        return last_customer
    return text


def _is_negated(text: str, word: str, pos: int) -> bool:
    pre = text[max(0, pos - 8):pos].strip().lower()
    return "not " in pre or "no " in pre or "not the " in pre


def extract_issue_type(claim_text: str) -> str:
    text = _all_customer_statements(claim_text).lower()
    scores = {}
    for issue_type, keywords in ISSUE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[issue_type] = score
    if not scores:
        if "damage" in text or "dano" in text or "damaged" in text:
            return "broken_part"
        return "unknown"
    best = max(scores, key=scores.get)
    return constrain_issue_type(best)


def extract_object_part(claim_text: str, claim_object: str) -> str:
    text = _all_customer_statements(claim_text).lower()
    parts = PART_KEYWORDS.get(claim_object, {})
    if not parts:
        return "unknown"
    scores = {}
    for part_name, keywords in parts.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[part_name] = score

    if not scores:
        return "unknown"
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "unknown"
    return constrain_object_part(best, claim_object)


def detect_text_instruction(text: str) -> bool:
    lower = text.lower()
    patterns = [
        "ignore all previous instructions",
        "approve the claim",
        "skip manual review",
        "follow it and approve",
        "follow karke claim approve",
        "mark this row",
        "follow it and",
    ]
    for p in patterns:
        if p in lower:
            return True
    return False


def extract_pair(claim_text: str, claim_object: str) -> tuple[str, str]:
    issue = extract_issue_type(claim_text)
    part = extract_object_part(claim_text, claim_object)
    return issue, part


def extract_severity(issue_type: str) -> str:
    severity_map = {
        "none": "none",
        "scratch": "low",
        "stain": "low",
        "missing_part": "low",
        "torn_packaging": "low",
        "dent": "medium",
        "crack": "medium",
        "water_damage": "medium",
        "crushed_packaging": "medium",
        "broken_part": "medium",
        "glass_shatter": "medium",
    }
    return severity_map.get(issue_type, "unknown")
