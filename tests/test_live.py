from __future__ import annotations

import os

import pytest

from waha_fast_mcp import server

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.getenv("WAHA_LIVE") != "1",
        reason="set WAHA_LIVE=1 and run a WAHA instance to enable live tests",
    ),
]


async def test_live_status():
    result = await server.waha_status()

    assert "version" in result
    assert "status" in result


async def test_live_sessions():
    result = await server.waha_list_sessions(include_stopped=True)

    assert isinstance(result["sessions"], list)


async def test_live_chats_are_bounded():
    sessions = await server.waha_list_sessions()
    working = [s for s in sessions["sessions"] if s["status"] == "WORKING"]
    if not working:
        pytest.skip("no working WAHA session")

    result = await server.waha_list_chats(working[0]["name"], limit=5)

    assert len(result["chats"]) <= 5
