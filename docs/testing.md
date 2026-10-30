# Testing: waha-fast-mcp

Inputs: [docs/design.md](./design.md), [docs/plan.md](./plan.md),
[docs/spec.md](./spec.md). Status: implemented.

## 1. Strategy

| Level | What it verifies | Network | Frequency |
| --- | --- | --- | --- |
| Unit | Client request shape, error mapping, compactors, media validation, tool delegation | Mocked | Every commit |
| Prompt | `waha_skill` returns `SKILL.md`; fallback is deterministic | None | Every PR |
| CLI | `--pretty` lists exactly 18 tools; module import works | None | Every PR |
| Integration | Real WAHA session, chats, messages, send | Live WAHA | Opt-in / nightly |
| Evals | Agent tool selection and send-safety behavior | Model + WAHA | Config change + schedule |
| Manual smoke | QR scan, real recipient confirmation | Live WhatsApp | Release |

**Single-command verification:**

```bash
uv run pytest
```

Supporting gates:

```bash
uv run ruff check .
uv run python -m waha_fast_mcp --pretty
```

## 2. Unit tests

### 2.1 Client and transport

- `WahaClient` builds `X-Api-Key` only when a key is present.
- `from_env()` reads `WAHA_BASE_URL`, `WAHA_API_KEY`, and `WAHA_TIMEOUT`.
- Session and chat IDs are URL-quoted with `safe=""`.
- Query parameters use lowercase booleans (`all=false`,
  `downloadMedia=false`).
- HTTP 500 raises `WahaError` containing status, method, and path.
- `httpx.ConnectError` raises `WahaError` with the method and path.
- 204 and empty bodies return `None`.
- `application/json` bodies are decoded; non-JSON bodies return `bytes`.
- Every client method maps to the expected method, path, and payload.

### 2.2 Helpers

- `_jid` handles serialized IDs, dict IDs, plain values, and `None`.
- `_compact_chat` returns the documented keys and flattens `lastMessage`.
- `_compact_message` returns the documented keys.
- `_file_payload` rejects zero and multiple sources.
- `_file_payload(path=...)` base64-encodes the file, infers MIME, and sets the
  filename.
- `_file_payload(path=...)` raises for a missing file.
- `_file_payload(data_base64=...)` defaults the MIME type.
- `_file_payload` preserves explicit `mimetype` and `filename`.

### 2.3 Tools

- `waha_status` returns version and server status.
- `waha_list_sessions` compacts session fields and passes `all`.
- `waha_list_chats` and `waha_get_chat_messages` apply compact projections.
- `waha_send_text` includes `reply_to` only when provided.
- `waha_send_image` and `waha_send_file` post the expected file payload.
- `waha_mark_chat_read` and `waha_set_typing` return deterministic strings.
- `waha_take_screenshot` writes bytes to the temp directory and reports the
  size.
- Tools close their client after the call.

### 2.4 Prompt and CLI

- `waha_skill()` returns the exact `SKILL.md` text.
- `_read_skill()` returns `SKILL_FALLBACK` when `_skill_path()` is `None`.
- `python -m waha_fast_mcp --pretty` returns valid JSON with 18 tools.
- `import waha_fast_mcp.server` succeeds (packaging regression guard).
- `waha_skill` appears in `mcp.list_prompts()`.

## 3. Integration tests (opt-in)

Set `WAHA_LIVE=1` and point `WAHA_BASE_URL` at a running WAHA instance. Tests are
marked `live` and skipped by default.

| # | Scenario | Expected |
| --- | --- | --- |
| I1 | `waha_status` | version and status returned; no exception |
| I2 | `waha_list_sessions(include_stopped=True)` | at least one session or an empty list |
| I3 | `waha_get_me` on a working session | account object with an ID |
| I4 | `waha_list_chats(limit=5)` | <= 5 compact chats |
| I5 | `waha_get_chat_messages(limit=5)` | <= 5 compact messages |
| I6 | screenshot | PNG bytes written; path exists |
| I7 | send to a test chat, then read it back | message ID appears; only run with explicit consent |

Do not run I7 in shared CI. Use a dedicated test recipient and short-lived
credentials.

## 4. Continuous evals

- **Corpus:** 20-50 real tasks: resolve a chat by name, summarize unread chats,
  send an approved text, send an image by URL, reject ambiguous media sources,
  handle a WAHA 500, and recover from a stale chat ID.
- **Runner:** fixed model, fixed tool config, non-interactive; record pass/fail,
  tool-call count, and any unapproved send.
- **Gates:** a change to `SKILL.md`, tool descriptions, or send behavior must not
  drop the pass rate. Any unapproved send is an automatic failure.
- **Ratchet:** every production incident becomes a permanent eval.
- **Baseline:** record the first green run before enabling the merge gate.

## 5. CI

- On PR: `uv sync --extra dev`, `uv run pytest`, `uv run ruff check .`, and the
  `--pretty` count check.
- Keep WAHA out of the default job. Run the live tier in a separate nightly or
  manually triggered job with a disposable WAHA and short-lived credentials.
- Block merge on failure. Require a human code-owner approval; the agent does
  not approve or merge its own change.
- Upload test output as evidence for the review.

## 6. Measurement

| Leading | Lagging |
| --- | --- |
| first-pass CI success on agent changes | review time; change failure rate |
| offline test count and coverage of tools | escaped defects |
| eval pass rate and zero unapproved sends | incidents reaching production |
| % of `SKILL.md` claims covered by a test | skill drift discovered late |

## 7. Definition of Done

- `uv run pytest` is green with no WAHA or WhatsApp available.
- Every one of the 18 tools has at least one unit test.
- Prompt fallback and wheel packaging are tested.
- Live integration tests are opt-in and documented.
- Ruff is clean; the catalog lists 18 tools.
- Evals and CI are tracked as follow-ups, not silently assumed.
