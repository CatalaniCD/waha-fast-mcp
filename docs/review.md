# Review instructions: waha-fast-mcp

Status: active. Applies to every PR and agent-generated change.

## 1. Passes

### Pass 1 - Bugs and contract preservation

- Do all 18 tool names, parameters, defaults, and response shapes match
  [spec.md](./spec.md)?
- Does the merged client preserve every HTTP method, path, query parameter, and
  JSON payload from the source project?
- Are async clients closed on success and on error?
- Does `--pretty` still avoid starting a server?
- Are media sources validated before any HTTP call?

### Pass 2 - Security and trust boundaries

- Is `WAHA_API_KEY` absent from tool arguments, prompt text, logs, and errors?
- Can an agent send, start, or stop without explicit user intent?
- Does any new code bypass `_file_payload` and read arbitrary local paths?
- Is the default transport still stdio? If HTTP is exposed, is the bind local
  and is authentication documented?
- Is `SKILL.md` treated as advisory, with hard controls implemented as hooks or
  host permission rules?

### Pass 3 - Spec, plan, and tests

- Does the change match [spec.md](./spec.md) and the current phase in
  [plan.md](./plan.md)?
- Is every new behavior covered by a test in [testing.md](./testing.md)?
- Were tests weakened, skipped, or deleted to make the change pass?
- Do the docs and `SKILL.md` still describe the real tool surface?
- Is the `SKILL.md` package-data path still correct for source and wheel use?

### Pass 4 - Readability and scope

- Is the change limited to the requested stage?
- Is `server.py` still one coherent module rather than a dumping ground?
- Are compact projections used instead of raw WAHA payloads where appropriate?
- Are new dependencies justified and pinned consistently?

## 2. What "Important" means

Report as important when a change:

- breaks a tool contract or a documented response shape,
- can send a message, start a session, or stop a session without explicit user
  intent,
- exposes the API key or reads a local file outside the documented media path,
- removes or weakens a test, or
- makes the default transport remotely reachable without authentication.

## 3. Severity

| Severity | Meaning | Action |
| --- | --- | --- |
| Critical | Unauthorized send, secret exposure, or unauthenticated remote access | Block merge; notify owner |
| High | Broken tool contract, data-loss path, or missing test for a new side effect | Block merge |
| Medium | Incorrect error handling, stale docs, or missing edge-case test | Fix before merge |
| Low | Naming, formatting, or non-behavioral docs polish | May follow up |

## 4. Cap the nits

At most five low-severity comments. Summarize the rest as one line. Do not
repeat the same nit across files.

## 5. Do not report

- Generated files, lockfiles, or `__pycache__`.
- Anything CI already enforces (formatting, lint, test pass).
- Re-litigating the conservative decision to keep all 18 tools.
- Requests for a generic `waha_request` tool; that is explicitly out of scope.
- Speculative multi-tenant or webhook work.

## 6. Evidence and gates

- The author must paste the output of `uv run pytest`, `uv run ruff check .`,
  and the 18-tool `--pretty` check.
- Agent review is advisory. A human code owner approves and merges.
- Changing send behavior, adding a generic request tool, or exposing HTTP
  transport requires explicit owner sign-off and an update to
  [design.md](./design.md).
- Every production incident becomes an eval case and, if it changes the
  contract, a new intent.
