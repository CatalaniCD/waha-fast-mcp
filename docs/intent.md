# Intent: waha-fast-mcp

Author: [unassigned]. Status: accepted.

## Problem

`waha-langchain-mcp` works, but its architecture is heavier than the fixed WAHA
REST API requires. HTTP concerns live in `client.py`, tool concerns live in
`server.py`, and every tool re-enters the process through a newly constructed
client. The server has 18 tools but no agent-facing procedural guide, so agents
must infer lifecycle, chat ID formats, media rules, and send safety from terse
tool descriptions.

The repository also lacks a verification path and a committed artifact chain:
there are no tests, no `SKILL.md`, and the README links to
`docs/architecture/waha-mcp.mmd` while the diagram actually lives under
`docs/diagrams/`.

The result is avoidable overhead for maintainers and avoidable misuse risk for
agents, especially around irreversible sends and local-file media.

## Proposed outcome

A new `waha-fast-mcp` project in this directory that:

- keeps all 18 existing tool names, signatures, and response shapes,
- merges the HTTP client and tool layer into one `src/waha_fast_mcp/server.py`,
- exposes a `waha_skill` MCP prompt backed by a versioned root `SKILL.md`,
- ships a pytest suite that runs without a live WAHA instance,
- keeps the LangChain ReAct and deep-agent examples working, and
- commits the full artifact chain under `docs/`.

## Affected users and systems

- **Primary users:** AI agents acting for a developer/operator through an MCP
  client (Claude Desktop, Cursor, LangChain).
- **Secondary users:** developers maintaining the WAHA integration and operators
  running the WAHA container.
- **Systems:** WAHA REST API at `http://localhost:3000`, a linked WhatsApp
  session, the MCP host, and the local filesystem for media paths.

## Constraints

- Preserve the existing 18 tool contracts; downstream prompts and examples must
  not need new tool names.
- Keep `WAHA_API_KEY` in the server environment; never expose it as a tool
  argument or prompt text.
- Default to stdio transport. Keep optional `sse` and `streamable-http` modes.
- Keep `requires-python = ">=3.10"` and the `mcp` 1.x SDK, which
  `langchain-mcp-adapters` still requires.
- Do not add a generic `waha_request` pass-through; WAHA is a fixed API and the
  escape hatch would increase agent risk without adding capability.
- Inbound WhatsApp events remain out of scope; use WAHA webhooks.

## Open questions

- Who is the accountable owner and which remote hosts the canonical repository?
- Should the tool surface be reduced later, after evals show which tools agents
  never use?
- Is a shared HTTP deployment required, and if so, which authentication layer
  and protected-chat policy apply?
- Should registered-chat allowlists be enforced by a host hook rather than by
  advice in `SKILL.md`?
