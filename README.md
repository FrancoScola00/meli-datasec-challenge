# MeLi DataSec Challenge — Leak Prevention

Four challenges for the Sr Cybersecurity Analyst (Leak Prevention) track. The
emphasis throughout is **verified correctness** and an explicit **leak-prevention
posture** (how sensitive data is handled), not just a working answer.

| # | Deliverable | What it is | Verified |
|---|-------------|-----------|----------|
| 1 | `solution_minesweeper.py` | Count neighbouring mines | ✅ pytest 12/12 (local) |
| 2 | `solution_best_in_genre.py` | Highest-rated TV show in a genre (paginated API) | ✅ pytest 9/9 mocked + ✅ live API |
| 3 | `applicant_query.sql` | Customers with >3 failed ad events (MySQL 8) | ✅ run on real MySQL 8.4.9 |
| 4 | `challenge4/` | LLM data-classification engine + PII redaction | ✅ pytest 16/16 + offline eval + ✅ live demo (free model) |

## Repository layout
```
solution_minesweeper.py     solution_best_in_genre.py     applicant_query.sql
challenge4/                  # LLM classifier (module + CLI + eval + live demo + DESIGN.md)
tests/                       # pytest suites + seed_and_check.sql + verify_c3.ps1
.claude/skills/              # 3 reusable Claude Code skills
requirements.txt  .python-version  Makefile  run.ps1  conftest.py
```

## Quickstart

### Windows (PowerShell)
```powershell
.\run.ps1 install      # create .venv (Python 3.12) and install pinned deps
.\run.ps1 test         # run the whole pytest suite
.\run.ps1 c1           # demo Challenge 1
.\run.ps1 c2 Action    # Challenge 2 against the live API -> "Game of Thrones"
.\run.ps1 c3-verify    # spin up a throwaway MySQL 8, load seed, run the query
```
If `.\run.ps1` is blocked by execution policy:
`powershell -ExecutionPolicy Bypass -File .\run.ps1 test`.

### Linux / macOS
```bash
make install   # python3.12 venv + pinned deps
make test
make c2        # live API
make c3-verify # requires a running MySQL 8 with a root user
```

### From scratch on a clean machine
1. Install **Python 3.12** (see `.python-version`). On Windows: `winget install Python.Python.3.12`.
2. `run.ps1 install` (or `make install`) to build `.venv` from `requirements.txt` (pinned).
3. `run.ps1 test` to verify everything offline. C2's live call and C4's live demo are the
   only steps that touch the network; both have offline-mocked tests too.

## Challenges

### 1 — Minesweeper (`solution_minesweeper.py`, Python 3.12)
`count_neighbouring_mines(board: list) -> list`. Returns a **new** matrix (input is
never mutated); mines become `9`, empty cells the count of the 8 neighbours. Handles
edges, corners, `[]`, 1×1, single row/column. Optional input validation raises only on
malformed input and does not change valid-input results.

### 2 — Best in genre (`solution_best_in_genre.py`, Python 3.12)
`bestInGenre(genre: str) -> str`. Walks all pages of
`jsonmock.hackerrank.com/api/tvseries`, splits the comma-separated `genre` field and
trims each part, matches case-insensitively, coerces `imdb_rating` to float
defensively, and breaks ties by alphabetical name. **Standard library only** (`urllib`)
to avoid third-party supply-chain surface; timeout + retry/backoff on the HTTP call.

### 3 — Advertising failures (`applicant_query.sql`, MySQL 8.x)
Joins `customers → campaigns → events`, filters `status='failure'`, groups per customer
(`GROUP BY c.id, c.first_name, c.last_name`, ONLY_FULL_GROUP_BY-safe), keeps
`HAVING COUNT(*) > 3`, orders by `failures DESC, customer ASC`. Verified output:
```
+-----------------+----------+
| customer        | failures |
+-----------------+----------+
| Whitney Ferrero |        6 |
+-----------------+----------+
```
`tests/verify_c3.ps1` reproduces this on a disposable MySQL 8 instance (it is **not**
a graded file).

### 4 — LLM data-classification engine (`challenge4/`)
Classifies text by `sensitivity` / `category` / `risk_score` / `confidence` /
`rationale`, with `needs_review` for abstention. See `challenge4/DESIGN.md` for the
full rationale.
```powershell
# offline eval (no network, deterministic)
.\.venv\Scripts\python.exe challenge4\eval\evaluate.py

# CLI (needs OPENROUTER_API_KEY)
.\.venv\Scripts\python.exe challenge4\classify_cli.py --text "email me at a@b.com"

# live demo (real call; runbook in the script header)
Copy-Item challenge4\.env.example challenge4\.env   # then add your key
.\.venv\Scripts\python.exe challenge4\demo_live.py --text "Card 4111 1111 1111 1111"
```

## Security reasoning per challenge (leak prevention)
- **C1** — no sensitive data; the security concern is correctness and **not mutating
  caller state** (avoid surprising side effects).
- **C2** — talks to an external service. We send no secrets, time out and retry
  bounded, and parse defensively so dirty/missing fields cannot crash or mislead.
  Stdlib-only keeps the dependency/supply-chain surface minimal.
- **C3** — the data is customer PII (names, event logs). The query reads the minimum
  needed and exposes only an aggregate (name + failure count). Suggested indexes
  (`events.campaign_id`, `events.status`, `campaigns.customer_id`) keep it efficient at
  scale without widening exposure.
- **C4** — the core leak-prevention exercise: PII is **redacted locally before** the
  text reaches the third-party LLM, only redacted text is logged, the sample is treated
  as untrusted data (prompt-injection defense), output is validated, and the engine
  **fails closed**. Secrets come from the environment only (`.env` is gitignored;
  `.env.example` documents the shape).

## Tooling / MCP note
The graded code depends on **no MCP** and no non-standard runtime. During development,
the built-in `WebFetch` tool was used to confirm the C2 API shape; the connected
`claude.ai` Gmail/Calendar/Drive MCP servers were deliberately **not** used (they carry
sensitive data and add nothing here). `git`/`gh` (CLI, not MCP) were used to publish.

## Verification status (honest)
- **Verified locally:** all pytest suites (C1 12, C2 9 mocked, C4 16), signature guards,
  import-has-no-side-effects, C4 offline eval, and C3 against real MySQL 8.4.9.
- **Verified against an external service:** C2's live API call returned `Game of Thrones`
  for `Action`; C4's **live** OpenRouter demo ran end-to-end on a free model
  (`nvidia/nemotron-nano-9b-v2:free`), redacting EMAIL/CARD/SSN/PHONE before the call and
  returning `RESTRICTED / PII`.
- **Not exhaustively verified:** C4's real-world accuracy at scale and the PII regex recall
  against adversarial formats — these need a larger labelled set and load testing.
