---
name: waha-fast-mcp
description: Operates a local WAHA (WhatsApp HTTP API) instance through MCP. Use to inspect sessions and chats, read messages, send text or media, and check contacts. Sending is an irreversible side effect and requires explicit user intent.
---

# Procedural guide: waha-fast-mcp

Use this guide when a task involves WhatsApp through WAHA. The server is
stateless: every call carries the WAHA session name, and WhatsApp state lives in
WAHA.

## 1. Non-negotiable safety rules

1. **Never invent chat IDs.** Resolve them with `waha_list_chats`,
   `waha_get_chat`, or `waha_check_number_exists`.
2. **Only send when the user explicitly asks.** `waha_send_text`,
   `waha_send_image`, and `waha_send_file` create real, irreversible messages.
   Do not send confirmations, summaries, or "test" messages unless instructed.
3. **Confirm the target before the first send.** State the session, chat ID,
   recipient name, and message preview, then wait for approval when the host
   supports a human gate.
4. **Never ask for or print the WAHA API key.** It is read from the server
   environment (`WAHA_API_KEY`) and must never appear in tool arguments, prompt
   text, or logs.
5. **Do not guess a session name.** Use `waha_list_sessions` first.
6. **Treat local paths as privileged.** `waha_send_image` and `waha_send_file`
   can read files from the server's filesystem. Only use a path the user
   explicitly supplied.

## 2. Operational lifecycle

Follow this order unless the user's request is narrower:

1. `waha_status` - confirm WAHA is reachable and note the version.
2. `waha_list_sessions` - pick a session whose status is `WORKING`.
3. `waha_get_me` (optional) - confirm the linked account before replying.
4. `waha_list_chats` - find the target chat and capture its `id`.
5. `waha_get_chat_messages` - read recent context.
6. Perform the requested read or write action.
7. Report the outcome using IDs and timestamps returned by the tools.

If `waha_status` fails, stop and report the error. Do not retry a write blindly.

## 3. Chat ID formats

| Suffix | Meaning | Example |
| --- | --- | --- |
| `@c.us` | Individual phone number | `5491123456789@c.us` |
| `@lid` | WhatsApp linked ID | `123456789012345@lid` |
| `@g.us` | Group | `120363012345678901@g.us` |

Pass the exact `id` returned by `waha_list_chats` or `waha_get_chat`. Do not
strip, reformat, or case-change it. For a raw phone number, call
`waha_check_number_exists` first; it returns the resolved WhatsApp identity.

## 4. Reading workflow

### Inspect chats

- `waha_list_chats(session, limit=20, offset=0)` returns newest-first summaries:
  `id`, `name`, `isGroup`, `unreadCount`, `timestamp`, `archived`, `pinned`,
  `muted`, and a compact `lastMessage`.
- Use small limits. Increase `offset` to page; do not request hundreds of chats
  at once.
- `waha_get_chat(session, chat_id)` returns the same compact shape for one chat.

### Read messages

- `waha_get_chat_messages(session, chat_id, limit=20, offset=0,
  download_media=False)` returns messages newest-first.
- Keep `download_media=False` unless the user asks for media. Media download is
  slower and can return large payloads.
- Use `hasMedia`, `type`, `fromMe`, `ackName`, `participant`, and `timestamp` to
  understand a message. `body` may be empty for media or protocol messages.
- Use message `id` values verbatim when replying with `reply_to`.

### Read state changes

- `waha_mark_chat_read(session, chat_id)` marks the chat read.
- `waha_set_typing(session, chat_id, typing=True|False)` toggles the indicator.
  Do not leave typing on after a failure.

## 5. Sending workflow

### Text

```
waha_send_text(session, chat_id, text, reply_to=None)
```

- Send plain text only. Do not embed secrets.
- Set `reply_to` to a message `id` only when quoting is requested.
- Re-read the tool result and report the returned message `id` and `timestamp`.

### Images and files

```
waha_send_image(session, chat_id, url=None, path=None, data_base64=None,
                filename=None, mimetype=None, caption=None)
waha_send_file(session, chat_id, url=None, path=None, data_base64=None,
               filename=None, mimetype=None, caption=None)
```

Provide **exactly one** source: `url`, `path`, or `data_base64`. Zero or
multiple sources fail validation.

- Prefer `url` when the user already has a reachable link.
- Prefer `path` for a local file the user named explicitly; the server base64
  encodes it.
- Use `data_base64` only when the host cannot provide a path or URL.
- Set `filename` and `mimetype` when they are not obvious from the source.
- Use `caption` sparingly; it is visible to the recipient.

## 6. Session administration

- `waha_create_session(name, start=True)` creates a session. A human must scan
  the QR code in the WAHA dashboard before it becomes `WORKING`.
- `waha_start_session(session)` starts a stopped session; QR scanning may be
  required.
- `waha_stop_session(session)` stops it without deleting data. This can
  disconnect the user's WhatsApp session; require explicit intent.
- `waha_get_session(session)` returns status and linked account details.
- Never create, start, or stop a session for a read-only task.

## 7. Contacts, profiles, and screenshots

- `waha_check_number_exists(session, phone)` expects digits with country code,
  no `+`, spaces, or dashes. Use it before sending to a raw number.
- `waha_get_profile_picture(session, contact_id)` accepts a chat or contact ID
  and returns the picture URL.
- `waha_take_screenshot(session)` saves a PNG and returns
  `{"path": ..., "bytes": ...}`. The path is on the server host. Do not claim
  the image is attached to a chat.

## 8. Errors and retries

- WAHA errors surface as tool errors containing the HTTP status and response
  body. Report the status and the relevant message; do not dump the full body
  if it may contain personal data.
- On a connection error, re-run `waha_status` once. If it still fails, stop.
- On `404` for a chat or session, re-list sessions/chats and re-resolve the ID
  instead of retrying the same ID.
- On `401` or `403`, report an API-key or permission problem. Never attempt to
  discover or bypass the key.
- Do not retry a send after a timeout until you have verified whether the
  message was delivered. Re-read the chat and look for the message ID first.
- On `ValueError` for media sources, correct the arguments; exactly one of
  `url`, `path`, or `data_base64` is required.

## 9. Response style

- Summarize what changed, not the raw JSON.
- Include session, chat ID, and message IDs when reporting a send.
- Distinguish reads from writes clearly.
- If a request is ambiguous, ask one focused question before sending.

## 10. Tool reference

| Tool | Purpose | Mutates WhatsApp |
| --- | --- | --- |
| `waha_status` | Connectivity, version, server status | No |
| `waha_list_sessions` | List sessions, optionally including stopped | No |
| `waha_get_session` | One session's status and account | No |
| `waha_get_me` | Linked account for a session | No |
| `waha_start_session` | Start a session | Yes |
| `waha_stop_session` | Stop a session | Yes |
| `waha_create_session` | Create a session | Yes |
| `waha_list_chats` | Recent chats | No |
| `waha_get_chat` | One chat's metadata | No |
| `waha_get_chat_messages` | Recent messages | No |
| `waha_send_text` | Send text | Yes |
| `waha_send_image` | Send an image | Yes |
| `waha_send_file` | Send a document | Yes |
| `waha_mark_chat_read` | Mark a chat read | Yes |
| `waha_set_typing` | Toggle typing indicator | Yes |
| `waha_check_number_exists` | Resolve a phone number | No |
| `waha_get_profile_picture` | Profile picture URL | No |
| `waha_take_screenshot` | Capture WAHA's screen | No |

## 11. Out of scope

Inbound WhatsApp events are not pushed over MCP. Use WAHA webhooks for
inbound automation. This server is request/response only.
