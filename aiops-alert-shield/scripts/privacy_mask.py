"""
scripts/privacy_mask.py
Deterministic PII and sensitive data redactor.
Masks credit cards, emails, auth tokens, JWTs, API keys, and phone numbers
while strictly preserving trace IDs, span IDs, service names, timestamps, and error codes.
"""

from __future__ import annotations
import re
import json
import sys
from pathlib import Path
from typing import Tuple, List, Dict, Any

# Compiled regex patterns for high performance and deterministic matching
CREDIT_CARD_REGEX = re.compile(
    r'\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{15,16}\b'
)
EMAIL_REGEX = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
)
BEARER_JWT_REGEX = re.compile(
    r'(?i)(Bearer\s+)[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*'
)
API_KEY_SECRET_REGEX = re.compile(
    r'(?i)(api[_-]?key|secret|password|auth[_-]?token|access[_-]?token|client[_-]?secret)\s*[:=]\s*["\']?([A-Za-z0-9_\-]{8,})["\']?'
)
PHONE_REGEX = re.compile(
    r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
)


def is_luhn_valid(n_str: str) -> bool:
    """Validate digits using Luhn formula to avoid false-masking pure numeric IDs."""
    digits = [int(c) for c in n_str if c.isdigit()]
    if len(digits) not in (13, 14, 15, 16, 19):
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = d * 2
            checksum += (doubled - 9) if doubled > 9 else doubled
        else:
            checksum += d
    return (checksum % 10) == 0


def mask_pii_text(text: str) -> Tuple[str, int, List[str]]:
    """
    Redact PII from a string while counting replacements and collecting categories.
    Returns: (redacted_text, redaction_count, redaction_types)
    """
    if not text:
        return text, 0, []

    redaction_count = 0
    redaction_types: List[str] = []

    # 1. Bearer / JWT Tokens
    def replace_bearer(match: re.Match) -> str:
        nonlocal redaction_count
        redaction_count += 1
        if "JWT_OR_BEARER" not in redaction_types:
            redaction_types.append("JWT_OR_BEARER")
        return f"{match.group(1)}[REDACTED_TOKEN]"

    masked = BEARER_JWT_REGEX.sub(replace_bearer, text)

    # 2. Key-value secrets (api_key=xxx, password=yyy)
    def replace_secret(match: re.Match) -> str:
        nonlocal redaction_count
        redaction_count += 1
        if "API_KEY_OR_SECRET" not in redaction_types:
            redaction_types.append("API_KEY_OR_SECRET")
        return f"{match.group(1)}=[REDACTED_SECRET]"

    masked = API_KEY_SECRET_REGEX.sub(replace_secret, masked)

    # 3. Emails
    def replace_email(match: re.Match) -> str:
        nonlocal redaction_count
        redaction_count += 1
        if "EMAIL" not in redaction_types:
            redaction_types.append("EMAIL")
        return "[REDACTED_EMAIL]"

    masked = EMAIL_REGEX.sub(replace_email, masked)

    # 4. Credit Cards (with length & formatting/Luhn check)
    def replace_card(match: re.Match) -> str:
        nonlocal redaction_count
        val = match.group(0)
        digits_only = re.sub(r'\D', '', val)
        if len(digits_only) in (15, 16) and (("-" in val or " " in val) or is_luhn_valid(digits_only)):
            redaction_count += 1
            if "CREDIT_CARD" not in redaction_types:
                redaction_types.append("CREDIT_CARD")
            return "[REDACTED_CREDIT_CARD]"
        return val

    masked = CREDIT_CARD_REGEX.sub(replace_card, masked)

    # 5. Phone numbers
    def replace_phone(match: re.Match) -> str:
        nonlocal redaction_count
        val = match.group(0)
        # Avoid masking hex strings or timestamps
        if re.search(r'[a-fA-F]', val) or len(val.strip()) < 10:
            return val
        redaction_count += 1
        if "PHONE_NUMBER" not in redaction_types:
            redaction_types.append("PHONE_NUMBER")
        return "[REDACTED_PHONE]"

    masked = PHONE_REGEX.sub(replace_phone, masked)

    return masked, redaction_count, redaction_types


def mask_log_entry(raw_log: Dict[str, Any]) -> Dict[str, Any]:
    """Applies PII redaction to a structured log record, returning RedactedLogEntry dict."""
    msg = raw_log.get("message", "")
    masked_msg, count, types = mask_pii_text(msg)
    return {
        "log_id": raw_log.get("log_id", f"log_{hash(msg) & 0xffffffff:08x}"),
        "timestamp": raw_log.get("timestamp", ""),
        "service": raw_log.get("service", "unknown"),
        "level": raw_log.get("level", "INFO"),
        "redacted_message": masked_msg,
        "trace_id": raw_log.get("trace_id"),
        "span_id": raw_log.get("span_id"),
        "redactions_count": count,
        "redaction_types": types,
    }


def main():
    """CLI testing / file stream processing."""
    sample = "User customer@example.com paid with 4532-0150-1234-5674 using api_key=sk_live_99214abc token Bearer eyJhbGciOi.eyJzdWIi.SflK"
    masked, count, types = mask_pii_text(sample)
    print("Sample Masking Test:")
    print("Input: ", sample)
    print("Output:", masked)
    print("Count: ", count)
    print("Types: ", types)


if __name__ == "__main__":
    main()
