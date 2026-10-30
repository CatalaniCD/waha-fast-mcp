from __future__ import annotations

import json

import httpx
import pytest

from waha_fast_mcp import server


def make_client(handler, **kwargs) -> server.WahaClient:
    options = {
        "base_url": "http://waha.test",
        "api_key": "secret",
        "transport": httpx.MockTransport(handler),
    }
    options.update(kwargs)
    return server.WahaClient(**options)


def test_from_env_reads_values(monkeypatch):
    monkeypatch.setenv("WAHA_BASE_URL", "http://wa.local:3001")
    monkeypatch.setenv("WAHA_API_KEY", "abc")
    monkeypatch.setenv("WAHA_TIMEOUT", "7.5")

    waha = server.WahaClient.from_env()

    assert waha.base_url == "http://wa.local:3001"
    assert waha.api_key == "abc"
    assert waha.timeout == 7.5


async def test_api_key_header_is_sent():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    async with make_client(handler) as waha:
        await waha.version()

    assert seen[0].headers["X-Api-Key"] == "secret"


async def test_no_api_key_header_when_empty():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    async with make_client(handler, api_key=None) as waha:
        await waha.version()

    assert "X-Api-Key" not in seen[0].headers


async def test_session_and_chat_ids_are_url_quoted():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    async with make_client(handler) as waha:
        await waha.get_chat("sess one", "549@c.us")

    assert seen[0].url.raw_path == b"/api/sess%20one/chats/549%40c.us"


async def test_list_sessions_uses_lowercase_booleans():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    async with make_client(handler) as waha:
        await waha.list_sessions(all=False)

    assert seen[0].url.params["all"] == "false"


async def test_http_error_maps_to_waha_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    async with make_client(handler) as waha:
        with pytest.raises(server.WahaError, match="WAHA 500 \\(GET /api/version\\)"):
            await waha.version()


async def test_transport_error_maps_to_waha_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async with make_client(handler) as waha:
        with pytest.raises(server.WahaError, match="WAHA request failed"):
            await waha.version()


async def test_204_and_empty_body_return_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    async with make_client(handler) as waha:
        assert await waha.mark_chat_read("s", "c@c.us") is None


async def test_non_json_body_returns_bytes():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"\x89PNG", headers={"content-type": "image/png"}
        )

    async with make_client(handler) as waha:
        assert await waha.screenshot("s") == b"\x89PNG"


async def test_json_body_is_decoded():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"version": "2026.1"})

    async with make_client(handler) as waha:
        assert await waha.version() == {"version": "2026.1"}


async def test_send_text_payload_includes_reply_to():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"id": "m1"})

    async with make_client(handler) as waha:
        await waha.send_text("s", "c@c.us", "hello", reply_to="m0")

    assert seen[0].url.path == "/api/sendText"
    assert json.loads(seen[0].content) == {
        "session": "s",
        "chatId": "c@c.us",
        "text": "hello",
        "reply_to": "m0",
    }
