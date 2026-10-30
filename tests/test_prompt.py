from __future__ import annotations

import asyncio
from pathlib import Path

from waha_fast_mcp import server

ROOT = Path(server.__file__).resolve().parents[2]


def test_skill_file_exists_at_repo_root():
    assert (ROOT / "SKILL.md").is_file()


def test_waha_skill_returns_skill_md():
    result = server.waha_skill()

    assert result == (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "Non-negotiable safety rules" in result


def test_waha_skill_fallback_when_missing(monkeypatch):
    monkeypatch.setattr(server, "_skill_path", lambda: None)

    assert server.waha_skill() == server.SKILL_FALLBACK


def test_waha_skill_is_registered_as_prompt():
    prompts = asyncio.run(server.mcp.list_prompts())
    names = {prompt.name for prompt in prompts}

    assert "waha_skill" in names
