# Python 3.12
"""Deterministic PII detection and masking.

Applied to every sample BEFORE it leaves the process for the LLM, so the third
party sees only redacted text (data-minimisation / least-exposure). Detection is
pure regex - no network, no model - so the act of detecting never exposes data.
Each match is replaced by a typed placeholder and counted by type.

Regex-based redaction is a deliberate trade-off: it is deterministic, auditable
and cheap, but pattern-based, so it can miss novel formats. It is a minimisation
control, not a guarantee; see DESIGN.md.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_TOKEN = re.compile(
    r"\b(?:"
    r"sk-ant-[A-Za-z0-9_-]{20,}"          # Anthropic
    r"|sk-proj-[A-Za-z0-9_-]{20,}"        # OpenAI project
    r"|sk-[A-Za-z0-9]{16,}"               # OpenAI / generic sk-
    r"|gh[opsu]_[A-Za-z0-9]{20,}"         # GitHub (gho_/ghp_/ghs_/ghu_)
    r"|github_pat_[A-Za-z0-9_]{20,}"      # GitHub fine-grained PAT
    r"|AKIA[0-9A-Z]{16}"                  # AWS access key id
    r"|AIza[0-9A-Za-z_-]{35,}"            # Google API key
    r"|(?:sk|rk|pk)_(?:live|test)_[0-9A-Za-z]{16,}"  # Stripe
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"      # Slack
    r")\b"
)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
_PRIVATE_KEY = re.compile(
    r"-----BEGIN[ A-Z0-9]*PRIVATE KEY-----.*?-----END[ A-Z0-9]*PRIVATE KEY-----",
    re.DOTALL,
)
_SECRET = re.compile(
    r"(?i)\b(?:password|passwd|pwd|contraseña|contrasena|clave"
    r"|secret|api[_-]?key|access[_-]?token|token)\b"
    r"\s*[=:]\s*[\"']?[^\s\"']+"
)
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
_CARD_CANDIDATE = re.compile(r"\b\d(?:[ -]?\d){12,18}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_SSN_BARE = re.compile(r"\b\d{9}\b")
_IPV4 = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
_PHONE = re.compile(r"(?<!\w)\+?\d[\d .\-]{5,13}\d(?!\w)")
# Prefix-less, high-entropy blob (a key/token a human might paste without a known
# prefix); only masked when it also passes _looks_like_secret (letters AND digits).
_GENERIC_SECRET = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9]{24,}(?![A-Za-z0-9])")
# Argentine national IDs (common in Spanish free-form input at MeLi).
_CUIT = re.compile(r"\b\d{2}-\d{8}-\d\b")
_DNI = re.compile(r"(?i)\bDNI[\s:]+(?:\d{1,2}\.\d{3}\.\d{3}|\d{7,8})\b")

# Zero-width / invisible characters an adversary can splice into a token to break
# a regex without changing how the text renders (ZWSP, ZWNJ, ZWJ, word joiner, BOM).
_ZERO_WIDTH = dict.fromkeys([0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF], None)


def _normalize(text: str) -> str:
    """Canonicalise text before detection so trivial obfuscations don't bypass it.

    NFKC folds full-width / homoglyph look-alikes to their ASCII form (e.g. the
    full-width digits ``１２３`` -> ``123``), and zero-width characters spliced into
    a token are stripped, so ``jo<ZWSP>hn@x.com`` is still detected. Decoding
    base64/hex is deliberately out of scope - too false-positive-prone for a
    redactor; see THREAT_MODEL.md.
    """
    return unicodedata.normalize("NFKC", text).translate(_ZERO_WIDTH)


def _luhn_ok(candidate: str) -> bool:
    """Validate a candidate card number with the Luhn checksum.

    Used to suppress false positives: only digit runs that pass Luhn are masked
    as cards (random 16-digit numbers are left for other detectors).
    """
    digits = [int(c) for c in candidate if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _looks_like_secret(candidate: str) -> bool:
    """True for high-entropy-looking blobs: long, with both letters and digits.

    Lets the generic catch-all mask prefix-less keys/tokens a human might paste,
    while leaving long plain words (no digit) and pure-digit runs (handled by the
    card/SSN/phone detectors) untouched.
    """
    return (
        len(candidate) >= 24
        and any(c.isalpha() for c in candidate)
        and any(c.isdigit() for c in candidate)
    )


def redact(text: str) -> tuple[str, dict[str, int]]:
    """Return ``(redacted_text, counts_by_type)``.

    Patterns are applied most-specific first so a broad detector (e.g. phone)
    cannot consume a more specific one (e.g. a Luhn-valid card). Credential
    detectors (private key, ``key=value`` secrets, JWT, API tokens) run first;
    IBAN runs before the card detector so an IBAN's digit run is never read as a
    card; a bare 9-digit SSN is matched before phone so it is labeled SSN, not
    PHONE. A bounded high-entropy catch-all (`_GENERIC_SECRET`) runs after the
    specific credential/email/IBAN detectors so they win, and before the numeric
    PII detectors; national IDs (CUIT/DNI) run before card/phone so their digit
    runs aren't mislabeled. A card-shaped run that fails Luhn is still redacted
    whole (as NUMBER, fail-safe) so the phone detector can't leak a fragment of it.

    Input is first NFKC-normalized and stripped of zero-width characters so
    homoglyph / invisible-character evasions cannot slip PII past the patterns.
    """
    text = _normalize(text)
    counts: dict[str, int] = {}

    def _apply(
        pattern: re.Pattern[str],
        label: str,
        value: str,
        validator: Callable[[str], bool] | None = None,
    ) -> str:
        def _replace(match: re.Match[str]) -> str:
            if validator is not None and not validator(match.group(0)):
                return match.group(0)
            counts[label] = counts.get(label, 0) + 1
            return f"[REDACTED_{label}]"

        return pattern.sub(_replace, value)

    text = _apply(_PRIVATE_KEY, "PRIVATE_KEY", text)
    text = _apply(_SECRET, "SECRET", text)
    text = _apply(_JWT, "JWT", text)
    text = _apply(_TOKEN, "TOKEN", text)
    text = _apply(_EMAIL, "EMAIL", text)
    text = _apply(_IBAN, "IBAN", text)
    text = _apply(_GENERIC_SECRET, "SECRET", text, validator=_looks_like_secret)
    text = _apply(_CARD_CANDIDATE, "CARD", text, validator=_luhn_ok)
    # Card-shaped run that fails Luhn: not a verified card, but redact the whole run
    # anyway (fail-safe) so the phone detector can't mask only part of it and leave
    # digits exposed. Labeled NUMBER, not CARD, to preserve the Luhn-verified distinction.
    text = _apply(_CARD_CANDIDATE, "NUMBER", text)
    text = _apply(_CUIT, "CUIT", text)
    text = _apply(_DNI, "DNI", text)
    text = _apply(_SSN, "SSN", text)
    text = _apply(_SSN_BARE, "SSN", text)
    text = _apply(_IPV4, "IP", text)
    text = _apply(_PHONE, "PHONE", text)
    return text, counts
