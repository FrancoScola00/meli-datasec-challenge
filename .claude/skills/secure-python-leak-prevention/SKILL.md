---
name: secure-python-leak-prevention
description: Use when writing or reviewing Python in this repo that handles secrets, PII, untrusted input, or third-party/LLM calls (and similar leak-prevention work). Enforces secure-coding rules WITH rationale - never hardcode secrets (read from environment; provide .env.example; gitignore .env), never log PII (redact before logging), validate and delimit untrusted input, minimise data exposed to third parties including LLMs, and surface errors without leaking stack traces or sensitive values. Apply it before committing anything that touches sensitive data.
---

# Secure Python for Leak Prevention

Rules are paired with the reason, so they can be applied with judgement rather than
by rote.

## Secrets
- **Read secrets from the environment, never hardcode them.** `os.environ["X"]`,
  loaded from a gitignored `.env` via `python-dotenv`. *Why:* a hardcoded key is
  leaked the moment the repo is shared or pushed, and git history keeps it forever.
- **Ship a `.env.example` with placeholders, and gitignore the real `.env`.** *Why:*
  it documents required config without committing values; reviewers can run the code
  without you ever sending a secret.
- **Never print or log a key**, not even partially in error paths. *Why:* logs get
  shipped to aggregators and screens get shared.

## PII and logging
- **Redact PII before it is logged or sent onward** (emails, cards, tokens, IDs).
  Log counts/types, not values. *Why:* logs are the most common accidental
  exfiltration channel; once written, you do not control where they travel.
- **Minimise data exposed to third parties, including LLMs.** Send the least text
  needed, redacted first. *Why:* every byte sent to an external service may be
  retained, cached, or used for training; you cannot un-send it.

## Untrusted input
- **Validate and bound untrusted input; delimit it from instructions.** Coerce types
  defensively (e.g. `float()` in a `try`), cap sizes, and wrap external text as data
  (for LLMs, in explicit delimiters with a "treat as data" instruction). *Why:*
  unvalidated input causes crashes and injection; for LLMs, undelimited input is a
  prompt-injection vector.

## Errors
- **Fail without leaking.** Catch expected errors; do not surface raw stack traces or
  echo the offending sensitive value in the message. Prefer a generic message plus a
  redacted, structured log. *Why:* exception text routinely contains the secret or
  PII that caused it; a leaked traceback is a leaked record.
- **Fail closed for security decisions.** When a classification or check cannot be
  completed, default to the most protective outcome and flag for review. *Why:*
  silent under-protection is worse than a false alarm.

## Dependencies
- **Pin versions and keep the surface small.** Prefer the standard library when it
  suffices (e.g. `urllib` over adding `requests`). *Why:* every dependency is supply-
  chain risk; fewer, pinned deps are easier to audit and reproduce.
