---
name: llm-data-classification
description: Use when building or modifying the Challenge 4 LLM data-classification engine, or any LLM pipeline that classifies or handles sensitive text. Covers a configurable sensitivity taxonomy, redacting PII BEFORE sending to the model, structured JSON output validated with pydantic plus a repair step, prompt-injection defense (treat the sample strictly as data), determinism (temperature=0), retry/backoff for 429 and fail-fast on 402, abstention on low confidence, and an offline eval harness for CI. Read REFERENCE.md for the detailed patterns and code shape.
---

# LLM Data Classification (Leak-Prevention)

Design an LLM classifier so the third-party model sees the least data possible, its
output is always validated, and the system fails closed. This file is the summary;
`REFERENCE.md` has the concrete patterns.

## The non-negotiables (and why)
1. **Redact PII locally, before any send.** Regex + Luhn for cards, run on the raw
   text; classify the *redacted* text. *Why:* using the LLM to find PII would require
   sending the PII first — defeating the purpose. Local detection never leaks.
2. **Treat the sample as data, not instructions.** Wrap it in delimiters and tell the
   system prompt to ignore any instruction inside it. *Why:* prompt injection — a
   sample can say "ignore previous instructions"; it must be classified, not obeyed.
3. **Structured output, validated.** `response_format={"type":"json_object"}` +
   pydantic (`extra="forbid"`) + taxonomy membership check + one repair retry. *Why:*
   models drift from schemas; validation + repair turns a soft contract into a hard one.
4. **Determinism.** `temperature=0`, fixed model, stable prompt. *Why:* a security
   control must be reproducible and auditable.
5. **Abstain, do not guess.** Low confidence → `needs_review`. Unparseable after
   repair → fail closed to the most sensitive level. *Why:* silent under-protection
   is the expensive failure mode for leak prevention.
6. **Configurable taxonomy.** Levels/categories from YAML, injected into the prompt —
   not hardcoded. *Why:* policy changes without code changes; the prompt stays in sync.
7. **Resilience + cost.** Backoff on 429/5xx, fail fast on 402 (no credit), track
   tokens. *Why:* batch workloads hit limits; retrying a billing error is pointless.

## Evaluate offline
Keep a small labelled golden set + recorded responses so the eval runs with no
network in CI, measuring per-class precision/recall. It tests the engine, not the
live model — keep that distinction explicit. See `REFERENCE.md`.
