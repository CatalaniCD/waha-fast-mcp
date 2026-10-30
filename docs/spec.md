# Spec: waha-fast-mcp

Status: accepted. Inputs: [docs/intent.md](./intent.md),
[docs/design.md](./design.md).

## 1. Functional requirements

| ID | Requirement | Acceptance |
| --- | --- | --- |
| FR-1 | Provide a Python package `waha_fast_mcp` with a `server.py` module. | `uv run python -c "import waha_fast_mcp.server"` succeeds. |
| FR-2 | `server.py` must contain the HTTP client, validation helpers, tools, prompt, and CLI entry point. | No `client.py` exists; all tool HTTP calls resolve inside `server.py`. |
| FR-3 | Preserve all 18 tool names and signatures from `waha-langchain-mcp`. | `python -m waha_fast_mcp --pretty` lists the 18 names in section 3. |
| FR-4 | Preserve compact chat and message response shapes. | `waha_list_chats` and `waha_get_chat_messages` return the documented keys only. |
| FR-5 | Expose an MCP prompt `waha_skill` that returns the contents of `SKILL.md`. | Prompt result equals the file text; missing file returns the documented fallback. |
| FR-6 | Default to stdio transport; support `sse` and `streamable-http`. | `--transport` accepts all three; env `WAHA_MCP_TRANSPORT` sets the default. |
| FR-7 | Support `--pretty` without starting a server. | Prints valid JSON tool catalog to stdout and exits 0. |
| FR-8 | Read `WAHA_BASE_URL`, `WAHA_API_KEY`, and `WAHA_TIMEOUT` from the environment / `.env`. | A client constructed with `from_env()` uses those values. |
| FR-9 | Raise `WahaError` for transport failures and HTTP status >= 400, including method, path, status, and a truncated body. | Mocked 500 and connection-error tests pass. |
| FR-10 | Enforce exactly one media source for send-image and send-file. | Zero or multiple sources raise `ValueError` before any HTTP call. |
| FR-11 | Keep the LangChain examples working against the new module. | `examples/common.py` spawns `python -m waha_fast_mcp`. |
| FR-12 | Provide a pytest suite that passes without WAHA or WhatsApp. | `uv run pytest` passes offline. |
| FR-13 | Provide the artifact chain under `docs/`. | All six documents exist and are linked from the README. |
| FR-14 | Ship `SKILL.md` as package data. | Built wheel contains `waha_fast_mcp/SKILL.md`; prompt works from an installed wheel. |

## 2. Tool contract

All tools are async and take `session` first. Chat IDs must be passed verbatim.

| Tool | Parameters | Returns |
| --- | --- | --- |
| `waha_status` | none | `{version, status}` raw WAHA payloads |
| `waha_list_sessions` | `include_stopped=False` | `{sessions: [{name, status, me}]}` |
| `waha_get_session` | `session` | Raw session object |
| `waha_get_me` | `session` | Raw account object (`id`, `lid`, `pushName`) |
| `waha_start_session` | `session` | Raw WAHA response |
| `waha_stop_session` | `session` | Raw WAHA response |
| `waha_create_session` | `name`, `start=True` | Raw WAHA response |
| `waha_list_chats` | `session`, `limit=20`, `offset=0` | `{chats: [CompactChat]}` |
| `waha_get_chat` | `session`, `chat_id` | `CompactChat` |
| `waha_get_chat_messages` | `session`, `chat_id`, `limit=20`, `offset=0`, `download_media=False` | `{messages: [CompactMessage]}` |
| `waha_send_text` | `session`, `chat_id`, `text`, `reply_to=None` | `CompactMessage` |
| `waha_send_image` | `session`, `chat_id`, `url=None`, `path=None`, `data_base64=None`, `filename=None`, `mimetype=None`, `caption=None` | `CompactMessage` |
| `waha_send_file` | same as `waha_send_image` | `CompactMessage` |
| `waha_mark_chat_read` | `session`, `chat_id` | `"Marked <chat_id> as read."` |
| `waha_set_typing` | `session`, `chat_id`, `typing=True` | `"Typing indicator started|stopped for <chat_id>."` |
| `waha_check_number_exists` | `session`, `phone` | Raw WAHA contact-check payload |
| `waha_get_profile_picture` | `session`, `contact_id` | Raw WAHA profile-picture payload |
| `waha_take_screenshot` | `session` | `{path, bytes}` on the server host |

### CompactChat

```text
id, name, isGroup, unreadCount, timestamp, archived, pinned, muted, lastMessage
lastMessage: {body, timestamp, fromMe} | null
```

### CompactMessage

```text
id, timestamp, from, to, fromMe, participant, body, type,
hasMedia, ackName, hasQuotedMsg
```

## 3. Validation and error semantics

- `session` and `chat_id` are URL-quoted with `safe=""`.
- Missing WAHA connection: `WahaError("WAHA request failed ...")`.
- HTTP >= 400: `WahaError("WAHA <status> (<method> <path>): <body[:1000]>")`.
- 204 or empty body: returns `None`.
- Non-JSON response (for example PNG screenshot): returns `bytes`.
- Media with zero or multiple sources: `ValueError("Provide exactly one of: url, path, data_base64")`.
- Media path missing: `ValueError("File not found: <path>")`.
- MIME type for a local path: explicit `mimetype`, else guessed, else
  `application/octet-stream`.

## 4. Compatibility

- Tool names, parameters, defaults, and response shapes match
  `waha-langchain-mcp` at commit `a180687`.
- `python -m waha_fast_mcp` and the `waha-fast-mcp` console script both start the
  server.
- Examples use the same environment variables and LangChain versions.
- Python 3.10+; `mcp` 1.x; `langchain-mcp-adapters` remains supported.

## 5. Non-goals

- Inbound WhatsApp events or webhook management.
- A generic `waha_request(method, path, body)` tool.
- Multi-tenant authentication or hosted deployment.
- Reducing or renaming the 18 tools.
- Message search, bulk sends, and scheduled messages.

## 6. Acceptance criteria

1. `uv sync --extra dev` completes.
2. `uv run pytest` passes with no network and no WAHA.
3. `uv run python -m waha_fast_mcp --pretty` returns exactly 18 tools.
4. `waha_skill` returns `SKILL.md`; the fallback is used if the file is absent.
5. `uv run ruff check .` passes.
6. README links resolve; all six docs exist.
7. Optional live smoke with `WAHA_LIVE=1` passes when WAHA is running.
