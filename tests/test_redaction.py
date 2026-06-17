# Python 3.12
"""Tests for the Challenge 4 PII redaction layer (pure, offline)."""
from classifier.redaction import _luhn_ok, redact


def test_email_is_redacted():
    out, counts = redact("contact me at john.doe@example.com please")
    assert "john.doe@example.com" not in out
    assert "[REDACTED_EMAIL]" in out
    assert counts["EMAIL"] == 1


def test_luhn_valid_card_is_redacted():
    out, counts = redact("pay with 4111 1111 1111 1111 today")
    assert "[REDACTED_CARD]" in out
    assert counts.get("CARD") == 1


def test_luhn_invalid_number_is_not_a_card():
    # Fails the Luhn checksum -> must not be masked as a card.
    out, counts = redact("ref 1234 5678 9012 3456 end")
    assert "CARD" not in counts


def test_luhn_helper():
    assert _luhn_ok("4111111111111111") is True
    assert _luhn_ok("4111111111111112") is False


def test_api_token_is_redacted():
    out, counts = redact("key=AKIAIOSFODNN7EXAMPLE done")
    assert "[REDACTED_TOKEN]" in out
    assert counts["TOKEN"] == 1


def test_ssn_is_redacted():
    out, counts = redact("ssn 123-45-6789 on file")
    assert "[REDACTED_SSN]" in out
    assert counts["SSN"] == 1


def test_ipv4_is_redacted():
    out, counts = redact("server 192.168.1.10 is down")
    assert "[REDACTED_IP]" in out
    assert counts["IP"] == 1


def test_clean_text_is_unchanged():
    text = "The weather is pleasant in spring."
    out, counts = redact(text)
    assert out == text
    assert counts == {}
