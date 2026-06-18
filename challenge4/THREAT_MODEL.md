# Challenge 4 — Threat model (MITRE ATLAS mapping)

This maps the controls already implemented in the classifier to the relevant
techniques in [MITRE ATLAS](https://atlas.mitre.org/) (the adversarial-ML
counterpart to ATT&CK). It documents what the pipeline defends against and is
explicit about residual risk — it is a threat model, not a guarantee. See
[DESIGN.md](DESIGN.md) for the rationale behind each control.

Technique IDs/names below were taken from the MITRE ATLAS dataset
(`mitre-atlas/atlas-data`).

## Adversary & assets
- **Assets:** the sensitive text being classified (PII/credentials/financial …)
  and the OpenRouter API key.
- **Untrusted boundary:** the sample text (attacker-controlled) and the LLM
  response (a third party we don't control).
- **Goal of the controls:** never expose raw sensitive data to the third-party
  model, and never let attacker text steer the classification.

## Mapping

### AML.T0057 LLM Data Leakage · AML.T0024 Exfiltration via AI Inference API
The core leak-prevention control. PII is detected and masked **before** any text
leaves the process (`classifier/redaction.py::redact`), so the model and the
provider see only redacted text. Logs emit only the redaction summary, never the
raw sample (`classifier/classify.py`), and the returned `ClassificationResult`
carries counts + label, never the original input (`classifier/models.py`).
*Residual:* regex recall is finite (see "Out of scope").

### AML.T0051 LLM Prompt Injection · AML.T0054 LLM Jailbreak
The sample is delimited and framed strictly as **data to classify, not
instructions** in the system prompt (`classifier/prompts.py`). Output is
constrained to the taxonomy and validated (pydantic `extra="forbid"` +
allow-listed labels); on low confidence the result abstains
(`needs_review=true`) and on invalid/unparseable output it **fails closed** to
the most-sensitive level (`classifier/classify.py`). Determinism is enforced with
`temperature=0` (`classifier/config.py`). Covered by
`tests/test_classifier.py` (`test_system_prompt_hardens_against_injection`,
`test_low_confidence_flags_needs_review`, `test_unrepairable_output_fails_closed`,
`test_off_taxonomy_label_is_rejected`).

### AML.T0056 Extract LLM System Prompt
The system prompt contains no secrets — only the taxonomy and instructions — so
there is nothing sensitive to recover by extracting it. The API key lives only in
the environment and is never placed in a prompt (`classifier/config.py`).

### AML.T0068 LLM Prompt Obfuscation · AML.T0015 Evade AI Model
Before detection, input is NFKC-normalized and stripped of zero-width characters
(`classifier/redaction.py::_normalize`), so homoglyph / full-width look-alikes
and invisible characters spliced into a token cannot smuggle PII past the regex
patterns (`tests/test_redaction.py::test_zero_width_split_email_is_redacted`,
`::test_fullwidth_digits_are_normalized_then_detected`).

## Out of scope / residual risk (honest)
- **Regex recall.** Redaction is a deterministic minimisation control, not a
  guarantee; novel PII formats can be missed (see DESIGN.md).
- **Encoded payloads.** Base64/hex/URL-encoded PII is **not** decoded before
  redaction — decoding is too false-positive-prone for a redactor. A
  defence-in-depth improvement would be an entropy/encoded-blob detector that
  masks high-entropy runs as a generic secret.
- **Model behaviour at scale.** Injection resistance is demonstrated by the tests
  above, not proven; real-world accuracy and adversarial robustness need a larger
  labelled set and live evaluation.
