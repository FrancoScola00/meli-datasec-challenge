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
    # Fails the Luhn checksum -> must not be labeled CARD (it is redacted as NUMBER).
    out, counts = redact("ref 1234 5678 9012 3456 end")
    assert "CARD" not in counts


def test_cardshaped_non_luhn_is_redacted_whole_not_split():
    # A card-shaped run that fails Luhn must be redacted as ONE unit (fail-safe),
    # never partially eaten by the phone detector leaving trailing digits exposed.
    out, counts = redact("tarjeta 4111 2222 3333 2222 ok")
    assert "2222" not in out            # no fragment of the run leaks
    assert "[REDACTED_NUMBER]" in out
    assert counts.get("NUMBER") == 1
    assert "CARD" not in counts         # not Luhn-valid -> not a confirmed card
    assert "PHONE" not in counts        # not split into a phone fragment


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


def test_jwt_is_redacted():
    jwt = (
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        "dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    )
    out, counts = redact(f"bearer {jwt} attached")
    assert jwt not in out
    assert "[REDACTED_JWT]" in out
    assert counts["JWT"] == 1


def test_private_key_block_is_redacted():
    # Ensamblado en runtime: evita que el delimitador PEM aparezca literal en el
    # fuente y dispare scanners de secretos (es un fixture, no una clave real).
    kind = "PRIVATE KEY"
    body = "MIIBVAIBADANBgkqhkiG9w0BAQEFAASCAT4wggE6AgEAAk\nEAfakekeymaterialfortestsonly0000=="
    block = f"-----BEGIN {kind}-----\n{body}\n-----END {kind}-----"
    out, counts = redact(f"key follows:\n{block}\nend")
    assert "PRIVATE KEY" not in out
    assert "[REDACTED_PRIVATE_KEY]" in out
    assert counts["PRIVATE_KEY"] == 1


def test_password_literal_is_redacted():
    out, counts = redact("login with password=hunter2 now")
    assert "hunter2" not in out
    assert "[REDACTED_SECRET]" in out
    assert counts["SECRET"] == 1


def test_secret_keyword_without_assignment_is_not_redacted():
    # Prose mentioning the keywords but with no '='/':' must be left intact.
    for text in ("password reset instructions", "the access token was revoked"):
        out, counts = redact(text)
        assert out == text
        assert "SECRET" not in counts


def test_iban_is_redacted_and_not_split_as_card():
    out, counts = redact("transfer to DE89370400440532013000 today")
    assert "DE89370400440532013000" not in out
    assert "[REDACTED_IBAN]" in out
    assert counts == {"IBAN": 1}


def test_bare_ssn_is_labeled_ssn():
    out, counts = redact("ssn 123456789 on file")
    assert "123456789" not in out
    assert "[REDACTED_SSN]" in out
    assert counts["SSN"] == 1
    assert "PHONE" not in counts


def test_zero_width_split_email_is_redacted():
    # A zero-width space (U+200B) spliced mid-token must not defeat detection.
    out, counts = redact("reach me at jo​hn.doe@example.com please")
    assert "[REDACTED_EMAIL]" in out
    assert "example.com" not in out
    assert counts["EMAIL"] == 1


def test_fullwidth_digits_are_normalized_then_detected():
    # Full-width digit homoglyphs (U+FF11..) fold to ASCII via NFKC, then caught.
    fullwidth = "１２３４５６７８９"  # 123456789
    out, counts = redact(f"ssn {fullwidth} on file")
    assert "[REDACTED_SSN]" in out
    assert counts["SSN"] == 1


# Secret-shaped test inputs are assembled from fragments so the contiguous literal
# never lands in the source (GitHub push protection blocks committed secret patterns);
# redact() still sees the joined string at runtime.
def test_anthropic_key_is_redacted():
    key = "sk-" + "ant-api03-AbcDef0123456789GhiJkl0123456789MnoP"
    out, counts = redact(f"usá {key} ahora")
    assert "sk-ant" not in out
    assert counts["TOKEN"] == 1


def test_google_api_key_is_redacted():
    key = "AIza" + "SyD0123456789abcdefghijklmnopqrstuvwxyz"
    out, counts = redact(f"key {key} here")
    assert "AIza" not in out
    assert counts["TOKEN"] == 1


def test_stripe_key_is_redacted():
    key = "sk_" + "live_" + "0000fakeStripeKey000000aa"
    out, counts = redact(f"stripe {key} done")
    assert "live_0000" not in out
    assert counts["TOKEN"] == 1


def test_github_pat_is_redacted():
    key = "ghp_" + "016C7f8a9b0c1d2e3f4g5h6i7j8k9l0m1n2o"
    out, counts = redact(f"token {key} end")
    assert "ghp_" not in out
    assert counts["TOKEN"] == 1


def test_prefixless_high_entropy_key_is_caught_by_generic():
    # A human pastes a key with no recognisable prefix (the demo's adversarial case).
    out, counts = redact("Te paso la api key nueva 'ant9879423429hlkjlkjn23423lk342ln' gracias")
    assert "ant9879423429hlkjlkjn23423lk342ln" not in out
    assert "[REDACTED_SECRET]" in out
    assert counts["SECRET"] == 1


def test_cuit_is_redacted():
    out, counts = redact("facturar al CUIT 20-12345678-3 por favor")
    assert "20-12345678-3" not in out
    assert counts["CUIT"] == 1


def test_dni_with_keyword_is_redacted():
    out, counts = redact("DNI: 12345678 verificado")
    assert "12345678" not in out
    assert counts["DNI"] == 1
    dotted_out, dotted_counts = redact("titular DNI 12.345.678 ok")
    assert "12.345.678" not in dotted_out
    assert dotted_counts["DNI"] == 1


def test_spanish_password_literal_is_redacted():
    out, counts = redact("la contraseña=hunter2 es secreta")
    assert "hunter2" not in out
    assert counts["SECRET"] == 1


def test_long_plain_word_is_not_over_redacted():
    # 24+ chars but letters only (no digit) -> generic catch-all must NOT fire.
    text = "Supercalifragilisticexpialidocious today"
    out, counts = redact(text)
    assert out == text
    assert counts == {}


def test_clean_text_is_unchanged():
    text = "The weather is pleasant in spring."
    out, counts = redact(text)
    assert out == text
    assert counts == {}
