# Plan: waha-fast-mcp

Inputs: [docs/intent.md](./intent.md), [docs/design.md](./design.md),
[docs/spec.md](./spec.md). Status: implemented; offline verification complete.

Order: make it run, make it equivalent, make it guided, make it verifiable.

## Phase 0 - Scaffold

- [x] **P0-1** Create the `src/waha_fast_mcp` package, `pyproject.toml`,
  `.env.example`, `.gitignore`, README, and LICENSE.
- [x] **P0-2** Keep `requires-python >=3.10`, `mcp>=1.24,<2.0`, `httpx`, and
  `python-dotenv`; add `dev` and `examples` extras. Remove the duplicate
  `langchain` dependency inherited from the source project.
- [x] **P0-3** Configure the console script `waha-fast-mcp` and a
  `python -m waha_fast_mcp` entry point.
- [x] **P0-4** Copy the LangChain examples and change the child module from
  `waha_mcp` to `waha_fast_mcp`.
- *Acceptance:* the package imports and the examples reference the new module.

## Phase 1 - Collapse the client into the server

- [x] **P1-1** Move `WahaClient` and `WahaError` into `server.py`; delete the
  standalone client module.
- [x] **P1-2** Add optional `httpx.AsyncBaseTransport` injection to
  `WahaClient` for offline tests.
- [x] **P1-3** Preserve every HTTP path, query parameter, and JSON payload from
  the source client.
- [x] **P1-4** Preserve all 18 tool signatures, compactors, media validation,
  and `--pretty` output.
- *Acceptance:* `python -m waha_fast_mcp --pretty` lists 18 tools and no
  `client.py` exists.

## Phase 2 - Add the operational skill

- [x] **P2-1** Write root `SKILL.md`: safety rules, lifecycle, chat ID formats,
  read/send/media workflows, session administration, errors, tool table, and
  out of scope.
- [x] **P2-2** Add `waha_skill` prompt with a safe fallback when the file is
  missing.
- [x] **P2-3** Force-include `SKILL.md` into the wheel as package data; resolve
  it from the repo root or package directory at runtime.
- *Acceptance:* the prompt returns the file in source and installed layouts.

## Phase 3 - Commit the artifact chain

- [x] **P3-1** Write `docs/intent.md`, `design.md`, `spec.md`, `plan.md`,
  `testing.md`, and `review.md`.
- [x] **P3-2** Update README links and remove the broken
  `docs/architecture/` reference.
- [x] **P3-3** Record the target architecture as a Mermaid diagram in
  `design.md`.
- *Acceptance:* every doc exists, is linked, and agrees on the 18-tool contract.

## Phase 4 - Tests and verification

- [x] **P4-1** Add `pytest`, `pytest-asyncio`, and `ruff` dev dependencies with
  `asyncio_mode = "auto"`.
- [x] **P4-2** Unit-test the merged client: request construction, quoting,
  non-2xx mapping, transport errors, 204, and binary responses.
- [x] **P4-3** Unit-test tools and helpers: compact projections, media
  validation, delegation, mutation messages, and screenshot output.
- [x] **P4-4** Test the prompt fallback and the `--pretty` catalog.
- [x] **P4-5** Add opt-in `WAHA_LIVE=1` integration tests against a real WAHA.
- [x] **P4-6** Run `uv sync`, `uv run pytest`, `uv run ruff check .`, and the
  catalog check; record the output in the review. Result: 41 passed, 3 live
  tests skipped; ruff clean; 18 tools listed; wheel contains
  `waha_fast_mcp/SKILL.md`.
- *Acceptance:* offline suite green, ruff clean, 18 tools listed.

## Phase 5 - Governance follow-ups

- [ ] **P5-1** Add a CI job for tests and ruff; sandbox with a disposable WAHA
  and short-lived credentials for the live tier.
- [ ] **P5-2** Add 20-50 non-interactive evals for tool selection and send
  safety, gated on `SKILL.md` or tool changes.
- [ ] **P5-3** Turn every production incident into a permanent eval case.
- [ ] **P5-4** If HTTP transport is exposed, add authentication and a
  localhost-only bind, and require a human gate for protected chats.

## Recommended sequence and rationale

P0 -> P1 -> P2 -> P4-2/3 -> P3 -> P4-6 -> P5. Establish a running and
behaviorally identical server, then make it guided, then prove it offline,
then document it, then automate gates. Do not add CI or evals before the manual
single-command loop is green.

## Measurement

| Stage | Leading indicator | Lagging indicator |
| --- | --- | --- |
| P0-P1 | package imports; 18 tools listed | tool-contract regressions |
| P2 | prompt resolves from source and wheel | agent misuse of sends or media |
| P3 | docs review complete | rework after implementation starts |
| P4 | first-pass `uv run pytest` success | escaped defects; rework rate |
| P5 | eval pass rate; CI coverage | incident rate; review time |

## Verification record

| Check | Result |
| --- | --- |
| `uv sync --extra dev` | 37 packages installed; project built |
| `uv run pytest -q` | 41 passed, 3 skipped (live tier) |
| `uv run ruff check .` | All checks passed |
| `python -m waha_fast_mcp --pretty` | 18 tools |
| Wheel inspection | `waha_fast_mcp/SKILL.md` present |
| Installed-wheel prompt | `waha_skill` returned 7899 characters |
| `WAHA_LIVE=1` live tier | Blocked by local 401 from a stale `WAHA_API_KEY`; rerun with the current WAHA key |

## Definition of Done

- The server starts from source and from the console script.
- All 18 tools are listed and their contracts match `spec.md`.
- `waha_skill` returns `SKILL.md`; the fallback is tested.
- `uv run pytest` passes offline; `uv run ruff check .` passes.
- The artifact chain is committed and linked from the README.
- A human code owner merges; the agent does not self-approve.
