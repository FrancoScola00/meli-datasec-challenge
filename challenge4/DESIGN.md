# Challenge 4 — Data Classification Engine: Design & Trade-offs

A leak-prevention engine that classifies short text samples by **sensitivity**,
**category** and **risk**, using an OpenAI-compatible LLM (OpenRouter). Security
posture is the priority: the third-party model sees the *least* data necessary,
output is validated, and the system fails closed.

## Pipeline (per sample)
```
raw text ─▶ redact PII (regex, local) ─▶ wrap as <sample> data ─▶ LLM (JSON, temp=0)
         ─▶ validate (pydantic + taxonomy) ─▶ [repair once] ─▶ abstain/fail-closed ─▶ result
```
The original text is never logged or sent — only the redacted version is. The
result object carries no raw input or PII, just the label plus a redaction summary.

## Key decisions

**Model choice (configurable, default `openai/gpt-4o-mini`).** The default is a
cheap, fast, JSON-reliable model — adequate for short-text classification and
inexpensive at batch scale. It is env-configurable (`CLASSIFIER_MODEL`, e.g.
`anthropic/claude-3.5-haiku` or a stronger model) because the right point on the
cost/accuracy curve depends on the data and budget. *Trade-off:* a small model is
cheaper but less accurate on ambiguous samples; the abstention threshold and the
eval harness exist precisely to make that trade-off measurable and safe.

**JSON mode vs function/tool calling.** We use `response_format={"type":"json_object"}`
plus pydantic validation plus a one-shot repair. *Trade-off:* tool/function calling
enforces a schema more strictly, but support varies across OpenRouter-proxied
providers; JSON mode is the portable lowest common denominator. We recover the lost
strictness in code (pydantic `extra="forbid"` + taxonomy membership + repair),
which also handles models that ignore `json_object`.

**Regex vs LLM for PII detection.** PII is detected and masked **locally with regex
before** anything is sent. *Trade-off:* regex misses novel formats (an LLM detector
would catch more), but using the model to find PII would require *sending the PII to
the model first* — exactly what we are trying to avoid. Local detection means the
act of detecting never leaks. Card numbers are Luhn-validated to cut false positives.
The detectors cover email; API tokens (OpenAI `sk-`/`sk-proj-`, Anthropic `sk-ant-`, AWS
`AKIA`, Google `AIza`, Stripe, GitHub, Slack); JWTs; PEM private-key blocks; `key=value`
secrets (English + Spanish keywords); a bounded high-entropy catch-all for prefix-less keys a
human might paste (≥24 chars with letters *and* digits); IBANs; Luhn-valid cards; Argentine
CUIT/DNI; SSNs (dashed and bare 9-digit); IPv4 and phone numbers. Patterns run most-specific
first so credentials, IBANs and national IDs are not eaten by the broader numeric detectors. Input is NFKC-normalized and stripped of zero-width characters
before detection, so homoglyph / invisible-character evasions can't smuggle PII past the regexes
(see THREAT_MODEL.md). This is a **minimisation control, not a guarantee**.

**Determinism.** `temperature=0`, a fixed model, and a stable prompt make runs
reproducible — important for auditing a security control and for stable evals.

**Cost vs accuracy.** Small default model + batch concurrency + token accounting
(`client.total_tokens`). Higher accuracy is one env var away when a sample stream
justifies it.

## Failure modes
- **Invalid/instruction-shaped JSON** → one bounded repair attempt (the schema error
  is fed back as data) → if still invalid, **fail closed**: label as the most
  sensitive level, `needs_review=true`, `error` populated. We never silently
  under-protect.
- **Low confidence** (`< CLASSIFIER_CONFIDENCE_THRESHOLD`) → `needs_review=true`
  instead of forcing a label (abstention/escalation).
- **Off-taxonomy label** → rejected by validation, treated like invalid output.
- **429 rate limit / 5xx / timeout** → exponential backoff retry. **402 (no credit)**
  → fail fast, since retrying cannot help.

## Prompt-injection defense
The sample is always wrapped in `<sample></sample>` and the system prompt instructs
the model to treat everything inside strictly as **data to classify, never as
instructions**. A sample containing "ignore previous instructions" is classified,
not obeyed. This is defense-in-depth, not a proof; combined with redaction it
limits both what a malicious sample can do and what it can exfiltrate.

## Explainability
Every result is meant to be actioned by a human, so it is explainable rather than a
bare label: alongside `sensitivity`/`category` it carries a `risk_score` (0-100), a
`confidence`, a short human-readable `rationale` for *why* the sample was rated that
way, and a `needs_review` flag. A reviewer sees the reasoning behind each decision,
which makes borderline calls auditable and lets false positives be triaged and
dismissed quickly instead of taken on faith.

## Observability
Structured logging emits only redacted summaries (counts by PII type, char length)
— never raw content. Token usage is tracked per client for cost monitoring.

## Evaluation & what is NOT verified
`eval/evaluate.py` runs the engine over a labelled golden set using **recorded**
responses (no network) and reports per-class precision/recall + accuracy. It is
deterministic and CI-safe, and it tests the **engine's** behaviour, not the live
model's. **Not verified here:** real end-to-end accuracy against a live model
(needs a key + a larger labelled set), latency/cost under real load, and recall of
the regex PII layer against adversarial real-world formats. The live path
(`demo_live.py`) is provided with a runbook but is only "working" once run with a
real key.

## Scaling to an agentic approach
This is a single-shot classifier by design (predictable, auditable, cheap). The
natural evolution the Leak-Prevention team values:
1. **Tools** — let the agent look up data lineage, owner, and prior classifications
   to ground its decision instead of judging text in isolation.
2. **Multi-step verification** — a second "challenger" pass (or a small judge panel)
   on `needs_review` items before a human sees them, raising precision.
3. **Human-in-the-loop queue** — `needs_review` feeds reviewers; their decisions
   become new golden-set rows (active learning), closing the feedback loop.
4. **Policy actions** — on RESTRICTED, the agent triggers downstream controls (block,
   quarantine, alert) via tools, turning classification into prevention.
Each step keeps the same guardrails: redact before send, validate output, fail
closed, measure with evals.
