"""Fast, single-module MCP server for WAHA (WhatsApp HTTP API).

The server merges the former HTTP client and tool layer into one module. It
exposes the same 18 tools as waha-langchain-mcp plus a ``waha_skill`` prompt
that returns the operational guide in ``SKILL.md``.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import mimetypes
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

SKILL_FALLBACK = (
    "Error: SKILL.md was not found. Reinstall waha-fast-mcp or read SKILL.md "
    "from the repository root."
)

mcp = FastMCP(
    "waha",
    instructions=(
        "Tools for a local WAHA (WhatsApp HTTP API) instance. Call waha_skill "
        "for the operational guide. Use waha_status first to confirm "
        "connectivity, then use the session name reported by waha_list_sessions. "
        "Chat IDs look like '<phone>@c.us', '<phone>@lid', or '<group-id>@g.us'. "
        "Sending messages is an irreversible side effect."
    ),
)


class WahaError(RuntimeError):
    """Raised when WAHA returns an error or cannot be reached."""


@dataclass(slots=True)
class WahaClient:
    """Async HTTP client for the WAHA REST API."""

    base_url: str = "http://localhost:3000"
    api_key: str | None = None
    timeout: float = 30.0
    transport: httpx.AsyncBaseTransport | None = None
    _http: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        self._http = httpx.AsyncClient(
            base_url=self.base_url.rstrip("/"),
            headers=headers,
            timeout=self.timeout,
            transport=self.transport,
        )

    @classmethod
    def from_env(cls) -> WahaClient:
        load_dotenv()
        return cls(
            base_url=os.getenv("WAHA_BASE_URL", "http://localhost:3000"),
            api_key=os.getenv("WAHA_API_KEY") or None,
            timeout=float(os.getenv("WAHA_TIMEOUT", "30")),
        )

    async def __aenter__(self) -> WahaClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise WahaError(f"WAHA request failed ({method} {path}): {exc}") from exc

        if response.status_code >= 400:
            raise WahaError(
                f"WAHA {response.status_code} ({method} {path}): "
                f"{response.text[:1000]}"
            )
        if response.status_code == 204 or not response.content:
            return None
        if "application/json" not in response.headers.get("content-type", ""):
            return response.content
        return response.json()

    @staticmethod
    def _session(session: str) -> str:
        return quote(session, safe="")

    @staticmethod
    def _chat(chat_id: str) -> str:
        return quote(chat_id, safe="")

    async def version(self) -> dict[str, Any]:
        return await self._request("GET", "/api/version")

    async def server_status(self) -> dict[str, Any]:
        return await self._request("GET", "/api/server/status")

    async def list_sessions(self, all: bool = False) -> list[dict[str, Any]]:
        return await self._request(
            "GET", "/api/sessions", params={"all": str(all).lower()}
        )

    async def get_session(self, session: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/sessions/{self._session(session)}")

    async def get_me(self, session: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"/api/sessions/{self._session(session)}/me"
        )

    async def create_session(self, name: str, start: bool = True) -> dict[str, Any]:
        return await self._request(
            "POST", "/api/sessions", json={"name": name, "start": start}
        )

    async def start_session(self, session: str) -> dict[str, Any]:
        return await self._request(
            "POST", f"/api/sessions/{self._session(session)}/start"
        )

    async def stop_session(self, session: str) -> dict[str, Any]:
        return await self._request(
            "POST", f"/api/sessions/{self._session(session)}/stop"
        )

    async def list_chats(
        self, session: str, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        return await self._request(
            "GET",
            f"/api/{self._session(session)}/chats",
            params={"limit": limit, "offset": offset},
        )

    async def get_chat(self, session: str, chat_id: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/api/{self._session(session)}/chats/{self._chat(chat_id)}",
        )

    async def get_messages(
        self,
        session: str,
        chat_id: str,
        limit: int = 20,
        offset: int = 0,
        download_media: bool = False,
    ) -> list[dict[str, Any]]:
        return await self._request(
            "GET",
            f"/api/{self._session(session)}/chats/{self._chat(chat_id)}/messages",
            params={
                "limit": limit,
                "offset": offset,
                "downloadMedia": str(download_media).lower(),
            },
        )

    async def get_message(
        self, session: str, chat_id: str, message_id: str
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/api/{self._session(session)}/chats/{self._chat(chat_id)}"
            f"/messages/{self._chat(message_id)}",
        )

    async def send_text(
        self,
        session: str,
        chat_id: str,
        text: str,
        reply_to: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "session": session,
            "chatId": chat_id,
            "text": text,
        }
        if reply_to:
            payload["reply_to"] = reply_to
        return await self._request("POST", "/api/sendText", json=payload)

    async def send_image(
        self,
        session: str,
        chat_id: str,
        file: dict[str, Any],
        caption: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "session": session,
            "chatId": chat_id,
            "file": file,
        }
        if caption:
            payload["caption"] = caption
        return await self._request("POST", "/api/sendImage", json=payload)

    async def send_file(
        self,
        session: str,
        chat_id: str,
        file: dict[str, Any],
        caption: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "session": session,
            "chatId": chat_id,
            "file": file,
        }
        if caption:
            payload["caption"] = caption
        return await self._request("POST", "/api/sendFile", json=payload)

    async def mark_chat_read(self, session: str, chat_id: str) -> Any:
        return await self._request(
            "POST",
            f"/api/{self._session(session)}/chats/{self._chat(chat_id)}"
            "/messages/read",
            json={},
        )

    async def start_typing(self, session: str, chat_id: str) -> Any:
        return await self._request(
            "POST",
            "/api/startTyping",
            json={"session": session, "chatId": chat_id},
        )

    async def stop_typing(self, session: str, chat_id: str) -> Any:
        return await self._request(
            "POST",
            "/api/stopTyping",
            json={"session": session, "chatId": chat_id},
        )

    async def check_number_exists(self, session: str, phone: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/contacts/check-exists",
            params={"session": session, "phone": phone},
        )

    async def profile_picture(self, session: str, contact_id: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/contacts/profile-picture",
            params={"session": session, "contactId": contact_id},
        )

    async def screenshot(self, session: str) -> bytes:
        return await self._request(
            "GET", "/api/screenshot", params={"session": session}
        )


def _jid(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("_serialized") or value.get("id")
    if value is None:
        return None
    return str(value)


def _compact_chat(chat: dict[str, Any]) -> dict[str, Any]:
    last = chat.get("lastMessage")
    last = last if isinstance(last, dict) else {}
    return {
        "id": _jid(chat.get("id")),
        "name": chat.get("name"),
        "isGroup": chat.get("isGroup"),
        "unreadCount": chat.get("unreadCount"),
        "timestamp": chat.get("timestamp"),
        "archived": chat.get("archived"),
        "pinned": chat.get("pinned"),
        "muted": chat.get("isMuted"),
        "lastMessage": {
            "body": last.get("body"),
            "timestamp": last.get("timestamp"),
            "fromMe": last.get("fromMe"),
        }
        if last
        else None,
    }


def _compact_message(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _jid(message.get("id")),
        "timestamp": message.get("timestamp"),
        "from": _jid(message.get("from")),
        "to": _jid(message.get("to")),
        "fromMe": message.get("fromMe"),
        "participant": _jid(message.get("participant")),
        "body": message.get("body"),
        "type": message.get("type"),
        "hasMedia": message.get("hasMedia"),
        "ackName": message.get("ackName"),
        "hasQuotedMsg": message.get("hasQuotedMsg"),
    }


def _file_payload(
    *,
    url: str | None,
    path: str | None,
    data_base64: str | None,
    filename: str | None,
    mimetype: str | None,
) -> dict[str, Any]:
    sources = [value for value in (url, path, data_base64) if value]
    if len(sources) != 1:
        raise ValueError("Provide exactly one of: url, path, data_base64")

    payload: dict[str, Any] = {}
    if url:
        payload["url"] = url
    elif path:
        file_path = Path(path).expanduser()
        if not file_path.is_file():
            raise ValueError(f"File not found: {file_path}")
        payload["data"] = base64.b64encode(file_path.read_bytes()).decode("ascii")
        payload["mimetype"] = (
            mimetype
            or mimetypes.guess_type(file_path.name)[0]
            or "application/octet-stream"
        )
        filename = filename or file_path.name
    else:
        payload["data"] = data_base64
        payload["mimetype"] = mimetype or "application/octet-stream"

    if filename:
        payload["filename"] = filename
    if mimetype and "mimetype" not in payload:
        payload["mimetype"] = mimetype
    return payload


def _client() -> WahaClient:
    return WahaClient.from_env()


def _skill_path() -> Path | None:
    candidates = [
        Path(__file__).resolve().parents[2] / "SKILL.md",
        Path(__file__).resolve().parent / "SKILL.md",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _read_skill() -> str:
    path = _skill_path()
    if path is None:
        return SKILL_FALLBACK
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return SKILL_FALLBACK


@mcp.prompt()
def waha_skill() -> str:
    """Return the WAHA operational guide and safety rules from SKILL.md."""
    return _read_skill()


@mcp.tool()
async def waha_status() -> dict[str, Any]:
    """Check WAHA connectivity and return server status and version."""
    async with _client() as waha:
        return {
            "version": await waha.version(),
            "status": await waha.server_status(),
        }


@mcp.tool()
async def waha_list_sessions(include_stopped: bool = False) -> dict[str, Any]:
    """List WhatsApp sessions. Set include_stopped to True to include stopped ones."""
    async with _client() as waha:
        sessions = await waha.list_sessions(all=include_stopped)
    return {
        "sessions": [
            {
                "name": session.get("name"),
                "status": session.get("status"),
                "me": session.get("me"),
            }
            for session in sessions
        ]
    }


@mcp.tool()
async def waha_get_session(session: str) -> dict[str, Any]:
    """Get one session, including its status and the linked WhatsApp account."""
    async with _client() as waha:
        return await waha.get_session(session)


@mcp.tool()
async def waha_get_me(session: str) -> dict[str, Any]:
    """Return the WhatsApp account (id, lid, pushName) linked to a session."""
    async with _client() as waha:
        return await waha.get_me(session)


@mcp.tool()
async def waha_start_session(session: str) -> dict[str, Any]:
    """Start a stopped WhatsApp session. Scan its QR code with the dashboard."""
    async with _client() as waha:
        return await waha.start_session(session)


@mcp.tool()
async def waha_stop_session(session: str) -> dict[str, Any]:
    """Stop a running WhatsApp session without deleting its data."""
    async with _client() as waha:
        return await waha.stop_session(session)


@mcp.tool()
async def waha_create_session(name: str, start: bool = True) -> dict[str, Any]:
    """Create a new WhatsApp session. Scan its QR code with the dashboard."""
    async with _client() as waha:
        return await waha.create_session(name, start=start)


@mcp.tool()
async def waha_list_chats(
    session: str, limit: int = 20, offset: int = 0
) -> dict[str, Any]:
    """List recent chats for a session, newest first."""
    async with _client() as waha:
        chats = await waha.list_chats(session, limit=limit, offset=offset)
    return {"chats": [_compact_chat(chat) for chat in chats]}


@mcp.tool()
async def waha_get_chat(session: str, chat_id: str) -> dict[str, Any]:
    """Get details about a chat. chat_id is like '549...@c.us' or '...@g.us'."""
    async with _client() as waha:
        return _compact_chat(await waha.get_chat(session, chat_id))


@mcp.tool()
async def waha_get_chat_messages(
    session: str,
    chat_id: str,
    limit: int = 20,
    offset: int = 0,
    download_media: bool = False,
) -> dict[str, Any]:
    """Read messages from a chat, newest first. Use the id from waha_list_chats."""
    async with _client() as waha:
        messages = await waha.get_messages(
            session,
            chat_id,
            limit=limit,
            offset=offset,
            download_media=download_media,
        )
    return {"messages": [_compact_message(message) for message in messages]}


@mcp.tool()
async def waha_send_text(
    session: str,
    chat_id: str,
    text: str,
    reply_to: str | None = None,
) -> dict[str, Any]:
    """Send a text WhatsApp message. Optionally pass reply_to as a message id."""
    async with _client() as waha:
        result = await waha.send_text(session, chat_id, text, reply_to=reply_to)
    return _compact_message(result)


@mcp.tool()
async def waha_send_image(
    session: str,
    chat_id: str,
    url: str | None = None,
    path: str | None = None,
    data_base64: str | None = None,
    filename: str | None = None,
    mimetype: str | None = None,
    caption: str | None = None,
) -> dict[str, Any]:
    """Send an image from a URL, local path, or base64 data, with optional caption."""
    file = _file_payload(
        url=url,
        path=path,
        data_base64=data_base64,
        filename=filename,
        mimetype=mimetype,
    )
    async with _client() as waha:
        result = await waha.send_image(session, chat_id, file, caption=caption)
    return _compact_message(result)


@mcp.tool()
async def waha_send_file(
    session: str,
    chat_id: str,
    url: str | None = None,
    path: str | None = None,
    data_base64: str | None = None,
    filename: str | None = None,
    mimetype: str | None = None,
    caption: str | None = None,
) -> dict[str, Any]:
    """Send a document from a URL, local path, or base64 data, with optional caption."""
    file = _file_payload(
        url=url,
        path=path,
        data_base64=data_base64,
        filename=filename,
        mimetype=mimetype,
    )
    async with _client() as waha:
        result = await waha.send_file(session, chat_id, file, caption=caption)
    return _compact_message(result)


@mcp.tool()
async def waha_mark_chat_read(session: str, chat_id: str) -> str:
    """Mark all messages in a chat as read."""
    async with _client() as waha:
        await waha.mark_chat_read(session, chat_id)
    return f"Marked {chat_id} as read."


@mcp.tool()
async def waha_set_typing(session: str, chat_id: str, typing: bool = True) -> str:
    """Show or hide the 'typing...' indicator in a chat."""
    async with _client() as waha:
        if typing:
            await waha.start_typing(session, chat_id)
        else:
            await waha.stop_typing(session, chat_id)
    state = "started" if typing else "stopped"
    return f"Typing indicator {state} for {chat_id}."


@mcp.tool()
async def waha_check_number_exists(session: str, phone: str) -> dict[str, Any]:
    """Check whether a phone number (digits only, with country code) has WhatsApp."""
    async with _client() as waha:
        return await waha.check_number_exists(session, phone)


@mcp.tool()
async def waha_get_profile_picture(session: str, contact_id: str) -> dict[str, Any]:
    """Get the profile picture URL for a contact or group."""
    async with _client() as waha:
        return await waha.profile_picture(session, contact_id)


@mcp.tool()
async def waha_take_screenshot(session: str) -> dict[str, Any]:
    """Capture the current WhatsApp Web screen and return the saved file path."""
    async with _client() as waha:
        data = await waha.screenshot(session)
    target = Path(tempfile.gettempdir()) / f"waha-{session}.png"
    target.write_bytes(data)
    return {"path": str(target), "bytes": len(data)}


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP server for WAHA")
    parser.add_argument(
        "--transport",
        default=os.getenv("WAHA_MCP_TRANSPORT", "stdio"),
        choices=["stdio", "sse", "streamable-http"],
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print the tool catalog as JSON and exit (no server is started).",
    )
    args = parser.parse_args()

    if args.pretty:
        tools = asyncio.run(mcp.list_tools())
        print(
            json.dumps(
                [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.model_dump(
                            by_alias=True, exclude_none=True
                        )["inputSchema"],
                    }
                    for tool in tools
                ],
                indent=2,
            )
        )
        return

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
