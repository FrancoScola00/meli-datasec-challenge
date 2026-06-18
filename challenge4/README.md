# Challenge 4 — LLM data-classification engine

A small, deterministic pipeline that classifies the sensitivity of a piece of
text with an LLM **without leaking it**: PII is redacted locally *before* the
text is sent to the third-party model, output is schema-validated, and the whole
thing fails closed.

```
raw text ─▶ redact PII (local regex) ─▶ wrap as <sample> data ─▶ LLM (JSON, temp=0)
         ─▶ validate (pydantic + taxonomy) ─▶ [repair once] ─▶ abstain / fail-closed ─▶ result
```

Each classification returns an **explainable** result — not just a label:
`sensitivity`, `category`, `risk_score` (0-100), `confidence`, a short `rationale`
(the "why"), a `needs_review` flag, and a `redactions` summary — so an analyst gets
the reasoning behind every decision.

See **[DESIGN.md](DESIGN.md)** for the rationale and trade-offs, and
**[THREAT_MODEL.md](THREAT_MODEL.md)** for the MITRE ATLAS mapping of the controls.

## Layout
```
classifier/            # the package
  redaction.py         #   PII detection + NFKC/zero-width normalization (runs BEFORE the LLM)
  prompts.py           #   system/user/repair prompt construction (sample framed as data)
  llm_client.py        #   OpenRouter client: JSON-only, temp=0, retry/backoff, 402 fail-fast
  classify.py          #   orchestration: redact → prompt → validate → repair → fail-closed
  config.py            #   taxonomy + env settings (validated; API key from env only)
  models.py            #   pydantic schemas (extra="forbid")
  batch.py  cli.py     #   batch helper + argparse CLI
eval/                  # offline, deterministic evaluation
  evaluate.py          #   metrics (accuracy + per-class precision/recall)
  golden_set.jsonl     #   8 labelled samples
  fixtures/responses.jsonl   # recorded LLM responses (no network in CI)
taxonomy.yaml          # sensitivity levels + categories (data-driven, editable)
.env.example           # required/optional environment variables
samples.txt            # example inputs for the batch demo
demo_live.py  demo_batch.py  classify_cli.py   # runnable entry points
DESIGN.md  THREAT_MODEL.md   # design rationale + MITRE ATLAS threat model
```

## Run
```bash
# from the repo root, with the venv active
cp challenge4/.env.example challenge4/.env   # then add your OPENROUTER_API_KEY

python challenge4/demo_live.py --text "..."          # single live classification (narrates the pipeline)
python challenge4/demo_batch.py                       # live batch over challenge4/samples.txt
python challenge4/classify_cli.py --help              # CLI entry point

python -m pytest tests/test_classifier.py tests/test_redaction.py tests/test_config.py -q   # 40 tests, offline
```
The offline tests and `eval/` need no API key or network — the LLM is mocked /
recorded. Only the `demo_*` scripts make a real call.
