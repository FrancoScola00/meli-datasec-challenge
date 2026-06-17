# Interview Prep — MeLi DataSec Challenge (Leak Prevention)

Likely questions per challenge, with a short answer and the trade-off I accept.

## Challenge 1 — Minesweeper (algorithmic)
- **Complexity?** O(R·C) time, O(R·C) extra space — each cell inspects 8 fixed
  neighbours (constant). *Trade-off:* the output matrix is unavoidable extra memory;
  if I had to be in-place I'd encode counts and mines in the same cell with bit/offset
  tricks, at the cost of readability.
- **Why not mutate the input?** Mutating a caller's argument is a hidden side effect
  that breaks reuse and concurrency, and here the algorithm needs the original mine
  layout while computing — overwriting cells would corrupt neighbour counts mid-pass.
- **Scale to huge boards?** It's already linear and streamable row-by-row; for sparse
  boards, iterate only mines and increment their neighbours (O(mines·8)). For massive
  boards, tile it and process blocks in parallel. *Trade-off:* sparse/tiled code is
  faster but more complex than the clear double loop, which I kept for a small board.
- **Why the validation helper?** It rejects malformed input (non-rectangular, values
  outside {0,1}) without changing results for valid input — fail-fast over silent
  garbage. *Trade-off:* a few cycles of validation for robustness.

## Challenge 2 — Best in genre (external API)
- **Pagination?** Read `total_pages` from page 1, then iterate `?page=1..total_pages`.
  *Trade-off:* sequential is simple and the dataset is tiny (20 pages); I'd parallelise
  page fetches only if it grew.
- **Idempotency?** `bestInGenre` is a pure read — safe to retry; no writes, no state.
- **Timeouts / retries?** Per-request timeout + bounded exponential backoff, so a slow
  or flaky endpoint fails predictably instead of hanging. *Trade-off:* retries add
  latency on real failures; capped at a few attempts.
- **Rate limiting?** Not hit at this size; at scale I'd add a token bucket and respect
  `Retry-After`. *Trade-off:* throughput vs. politeness to the API.
- **Nonexistent genre / dirty data?** Unknown genre returns `""` (typed `str`).
  Missing/non-numeric `imdb_rating` and non-string names are skipped, not crashed.
- **int vs float rating?** `imdb_rating` can be `9` or `9.3`; I coerce with `float()`
  in a guarded way so `9 > 8.9` compares correctly.
- **Why stdlib `urllib`, not `requests`?** Fewer dependencies = smaller supply-chain
  surface and easier reproducibility. *Trade-off:* `urllib` is more verbose; acceptable
  for one GET.
- **Why mock the HTTP in tests?** The grader's network may be down; mocked tests prove
  pagination, multi-genre split, case-insensitivity, tie-break, and int/float — offline
  and deterministically. The one live call is reported separately and honestly.

## Challenge 3 — SQL (advertising failures)
- **Why `CONCAT(first_name,' ',last_name)`?** The spec wants a single `customer`
  column as the full name.
- **Why `HAVING COUNT(*) > 3` and not `WHERE`?** The count is an aggregate; `WHERE`
  filters rows before grouping, `HAVING` filters groups after. Strictly `> 3` (4+),
  so Dickie Romera's 3 is excluded.
- **ONLY_FULL_GROUP_BY?** MySQL 8 enables it by default: every non-aggregated selected
  column must be in `GROUP BY`. I group by `c.id, c.first_name, c.last_name` — `id`
  guarantees correctness even if two customers share a name.
- **Suggested indexes?** `events.campaign_id` (join), `events.status` (filter; or a
  composite `(campaign_id, status)`), and `campaigns.customer_id` (join). They turn
  full scans into index lookups as the events table grows.
- **Performance at scale?** Events is the big table; the composite
  `(status, campaign_id)` index lets the filter+join stay sargable. *Trade-off:*
  indexes speed reads but cost write throughput and storage — justified because events
  are appended and this report is read often.
- **Deterministic ordering?** `ORDER BY failures DESC, customer ASC` — the tie-breaker
  makes output stable without changing the expected single row.

## Challenge 4 — LLM classification (the leak-prevention core)
- **Why an LLM and not just rules?** Regex catches *known* patterns (and we DO use it
  for PII detection); judging *sensitivity/category* of free text — tone, context,
  intent — is where an LLM generalises beyond brittle rules. *Trade-off:* cost,
  latency and nondeterminism, which I contain with temp=0, validation and evals.
- **Prompt-injection defense?** The sample is wrapped in `<sample>` tags and the system
  prompt says treat everything inside strictly as data, never instructions. A sample
  saying "ignore previous instructions" is classified, not obeyed. *Trade-off:* defense-
  in-depth, not a proof — paired with redaction to limit blast radius.
- **Why redact PII *before* sending?** Data minimisation: the third-party model should
  see the least sensitive data possible, and using the LLM to find PII would require
  sending the PII first. Local regex+Luhn detection means detecting never leaks.
  *Trade-off:* regex misses novel formats — a minimisation control, not a guarantee.
- **Determinism?** temp=0 + fixed model + stable prompt → reproducible, auditable
  security control and stable evals.
- **Structured output + validation?** JSON mode + pydantic (`extra="forbid"`) +
  taxonomy check + one repair retry; unparseable → fail closed. *Trade-off:* JSON mode
  is portable but loosely enforced vs. function-calling; I recover strictness in code.
- **Evals / metrics?** Offline golden set + recorded responses → per-class
  precision/recall + accuracy, deterministic for CI. It measures the *engine*, not the
  live model — I keep that distinction explicit.
- **Hallucinations / abstention?** Low confidence → `needs_review` instead of a forced
  label; off-taxonomy or invalid output → fail closed to the most sensitive level.
- **Cost / latency?** Small default model, batch concurrency, token tracking; the model
  is one env var away from a stronger one when data justifies it.
- **Data-minimisation angle (leak prevention)?** Redact-before-send, log only redacted
  text, no raw input in results, secrets from env only — every layer reduces what can
  leak to logs or a third party.
- **Evolve to an agent?** Tools for data lineage/owner lookup, a challenger/verifier
  pass on `needs_review`, a human-in-the-loop queue feeding active learning, and policy
  actions (block/quarantine/alert) on RESTRICTED — same guardrails throughout.

## General security
- **Secret management?** Environment only; `.env` gitignored; `.env.example` documents
  the shape; nothing secret in code or git history.
- **Minimal exposure?** Send/log/store the least sensitive data needed; redact first.
- **Errors without leaking?** Catch expected failures, emit generic messages + redacted
  structured logs; never surface a raw traceback that may embed PII/secrets.
- **Supply chain?** Pinned versions, stdlib-first (C1–C3 add no deps), small audited
  dependency set for C4.

## AI engineering / Claude Code
- **Skills used?** Three: `meli-challenge-contract` (locks the graded names/signatures),
  `secure-python-leak-prevention` (secure-coding rules with rationale), and
  `llm-data-classification` (the C4 pipeline). Descriptions are third-person with
  concrete triggers so they auto-activate at the right moment.
- **Progressive disclosure?** Each `SKILL.md` is short; the long C4 detail lives in
  `REFERENCE.md`, loaded only when needed — keeps context lean while staying complete.
- **MCP with judgement?** Built-in `WebFetch` confirmed the C2 API shape in dev; the
  connected Gmail/Calendar/Drive MCPs were deliberately not used (sensitive data, no
  value here). The deliverable depends on no MCP — a leak-prevention stance: more MCP
  is not better, real value and minimal exposure are.
