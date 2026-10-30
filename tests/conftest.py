from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from waha_fast_mcp import server


@pytest.fixture
def install_mock(monkeypatch):
    """Install a fresh MockTransport-backed WahaClient for every tool call."""

    def install(handler: Callable[[httpx.Request], httpx.Response]) -> None:
        def factory() -> server.WahaClient:
            return server.WahaClient(
                base_url="http://waha.test",
                api_key="test-key",
                transport=httpx.MockTransport(handler),
            )

        monkeypatch.setattr(server, "_client", factory)

    yield install


def json_response(payload: Any) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return handler


def capture_json(
    payload: Any, calls: list[httpx.Request]
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=payload)

    return handler


def body(request: httpx.Request) -> Any:
    return json.loads(request.content) if request.content else None
