from __future__ import annotations

import base64
import json
from pathlib import Path

import httpx
import pytest

from waha_fast_mcp import server


def body(request: httpx.Request) -> dict:
    return json.loads(request.content) if request.content else {}


async def test_waha_status(install_mock):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "2026.1"})
        return httpx.Response(200, json={"status": "ok"})

    install_mock(handler)

    result = await server.waha_status()

    assert result == {"version": {"version": "2026.1"}, "status": {"status": "ok"}}


async def test_list_sessions_compacts_and_passes_include_stopped(install_mock):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json=[
                {
                    "name": "session1",
                    "status": "WORKING",
                    "me": {"id": "549@c.us"},
                    "engine": "WEBJS",
                }
            ],
        )

    install_mock(handler)

    result = await server.waha_list_sessions(include_stopped=True)

    assert result == {
        "sessions": [
            {"name": "session1", "status": "WORKING", "me": {"id": "549@c.us"}}
        ]
    }
    assert seen[0].url.params["all"] == "true"


async def test_get_session_and_get_me(install_mock):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/me"):
            return httpx.Response(200, json={"id": "549@c.us", "pushName": "Me"})
        return httpx.Response(200, json={"name": "session1", "status": "WORKING"})

    install_mock(handler)

    session = await server.waha_get_session("session1")
    me = await server.waha_get_me("session1")

    assert session["status"] == "WORKING"
    assert me["pushName"] == "Me"


@pytest.mark.parametrize(
    ("tool", "suffix"),
    [
        (server.waha_start_session, "/start"),
        (server.waha_stop_session, "/stop"),
    ],
)
async def test_start_and_stop_session(install_mock, tool, suffix):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    install_mock(handler)

    result = await tool("session1")

    assert result == {"ok": True}
    assert seen[0].method == "POST"
    assert seen[0].url.path == f"/api/sessions/session1{suffix}"


async def test_create_session(install_mock):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"name": "new", "status": "STARTING"})

    install_mock(handler)

    result = await server.waha_create_session("new", start=False)

    assert result["name"] == "new"
    assert seen[0].method == "POST"
    assert seen[0].url.path == "/api/sessions"
    assert body(seen[0]) == {"name": "new", "start": False}


async def test_list_chats_compacts(install_mock):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json=[
                {
                    "id": {"_serialized": "549@c.us"},
                    "name": "Ada",
                    "isGroup": False,
                    "unreadCount": 2,
                    "timestamp": 100,
                    "archived": False,
                    "pinned": True,
                    "isMuted": False,
                    "lastMessage": {
                        "body": "hello",
                        "timestamp": 99,
                        "fromMe": False,
                        "extra": "drop",
                    },
                }
            ],
        )

    install_mock(handler)

    result = await server.waha_list_chats("session1", limit=5, offset=10)

    assert result["chats"][0]["id"] == "549@c.us"
    assert result["chats"][0]["lastMessage"] == {
        "body": "hello",
        "timestamp": 99,
        "fromMe": False,
    }
    assert "extra" not in result["chats"][0]
    assert seen[0].url.params["limit"] == "5"
    assert seen[0].url.params["offset"] == "10"


async def test_get_chat_compacts(install_mock):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "549@c.us", "name": "Ada"})

    install_mock(handler)

    result = await server.waha_get_chat("session1", "549@c.us")

    assert result["id"] == "549@c.us"
    assert result["name"] == "Ada"


async def test_get_chat_messages_compacts(install_mock):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json=[
                {
                    "id": {"_serialized": "m1"},
                    "timestamp": 100,
                    "from": {"_serialized": "549@c.us"},
                    "to": {"_serialized": "123@c.us"},
                    "fromMe": False,
                    "participant": None,
                    "body": "hello",
                    "type": "chat",
                    "hasMedia": False,
                    "ackName": "READ",
                    "hasQuotedMsg": False,
                    "extra": "drop",
                }
            ],
        )

    install_mock(handler)

    result = await server.waha_get_chat_messages(
        "session1", "549@c.us", limit=3, offset=1, download_media=True
    )

    message = result["messages"][0]
    assert message["id"] == "m1"
    assert message["from"] == "549@c.us"
    assert "extra" not in message
    assert seen[0].url.params["downloadMedia"] == "true"
    assert seen[0].url.params["limit"] == "3"


async def test_send_text_compacts_result(install_mock):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200, json={"id": "m1", "fromMe": True, "body": "hello", "extra": "drop"}
        )

    install_mock(handler)

    result = await server.waha_send_text("session1", "549@c.us", "hello")

    assert result["id"] == "m1"
    assert result["fromMe"] is True
    assert "extra" not in result
    assert body(seen[0]) == {
        "session": "session1",
        "chatId": "549@c.us",
        "text": "hello",
    }


async def test_send_image_from_url(install_mock):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"id": "m1", "type": "image"})

    install_mock(handler)

    await server.waha_send_image(
        "session1", "549@c.us", url="https://example.com/a.png", caption="hi"
    )

    assert seen[0].url.path == "/api/sendImage"
    assert body(seen[0]) == {
        "session": "session1",
        "chatId": "549@c.us",
        "file": {"url": "https://example.com/a.png"},
        "caption": "hi",
    }


async def test_send_file_from_path(install_mock, tmp_path: Path):
    source = tmp_path / "note.txt"
    source.write_text("hello file", encoding="utf-8")
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"id": "m1", "type": "document"})

    install_mock(handler)

    await server.waha_send_file("session1", "549@c.us", path=str(source))

    payload = body(seen[0])
    assert seen[0].url.path == "/api/sendFile"
    assert payload["file"]["filename"] == "note.txt"
    assert payload["file"]["mimetype"] == "text/plain"
    assert base64.b64decode(payload["file"]["data"]).decode() == "hello file"


async def test_send_image_rejects_zero_or_multiple_sources(install_mock):
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP must not be called for invalid media")

    install_mock(handler)

    with pytest.raises(ValueError, match="exactly one"):
        await server.waha_send_image("session1", "549@c.us")
    with pytest.raises(ValueError, match="exactly one"):
        await server.waha_send_image(
            "session1", "549@c.us", url="https://example.com/a.png", data_base64="aaa"
        )


async def test_mark_chat_read(install_mock):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(204)

    install_mock(handler)

    result = await server.waha_mark_chat_read("session1", "549@c.us")

    assert result == "Marked 549@c.us as read."
    assert seen[0].url.path == "/api/session1/chats/549@c.us/messages/read"


async def test_set_typing_true_and_false(install_mock):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    install_mock(handler)

    started = await server.waha_set_typing("session1", "549@c.us", typing=True)
    stopped = await server.waha_set_typing("session1", "549@c.us", typing=False)

    assert started == "Typing indicator started for 549@c.us."
    assert stopped == "Typing indicator stopped for 549@c.us."
    assert seen[0].url.path == "/api/startTyping"
    assert seen[1].url.path == "/api/stopTyping"
    assert body(seen[0]) == {"session": "session1", "chatId": "549@c.us"}


async def test_check_number_exists(install_mock):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"exists": True, "chatId": "549@c.us"})

    install_mock(handler)

    result = await server.waha_check_number_exists("session1", "5491123456789")

    assert result["exists"] is True
    assert seen[0].url.path == "/api/contacts/check-exists"
    assert seen[0].url.params["phone"] == "5491123456789"


async def test_get_profile_picture(install_mock):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"url": "https://example.com/p.png"})

    install_mock(handler)

    result = await server.waha_get_profile_picture("session1", "549@c.us")

    assert result["url"] == "https://example.com/p.png"
    assert seen[0].url.params["contactId"] == "549@c.us"


async def test_take_screenshot_writes_file(install_mock, tmp_path: Path, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"png-bytes", headers={"content-type": "image/png"}
        )

    install_mock(handler)
    monkeypatch.setattr(server.tempfile, "gettempdir", lambda: str(tmp_path))

    result = await server.waha_take_screenshot("session1")

    target = tmp_path / "waha-session1.png"
    assert result == {"path": str(target), "bytes": 9}
    assert target.read_bytes() == b"png-bytes"
