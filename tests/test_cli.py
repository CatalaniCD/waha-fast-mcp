from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from waha_fast_mcp import server

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TOOLS = {
    "waha_status",
    "waha_list_sessions",
    "waha_get_session",
    "waha_get_me",
    "waha_start_session",
    "waha_stop_session",
    "waha_create_session",
    "waha_list_chats",
    "waha_get_chat",
    "waha_get_chat_messages",
    "waha_send_text",
    "waha_send_image",
    "waha_send_file",
    "waha_mark_chat_read",
    "waha_set_typing",
    "waha_check_number_exists",
    "waha_get_profile_picture",
    "waha_take_screenshot",
}


def test_module_imports():
    assert server.mcp.name == "waha"


def test_pretty_prints_all_tools():
    env = os.environ.copy()
    source = str(ROOT / "src")
    env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [sys.executable, "-m", "waha_fast_mcp", "--pretty"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    catalog = json.loads(result.stdout)
    names = {tool["name"] for tool in catalog}
    assert names == EXPECTED_TOOLS
    assert len(catalog) == 18


def test_every_tool_has_a_description():
    tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}

    assert set(tools) == EXPECTED_TOOLS
    for tool in tools.values():
        assert tool.description
