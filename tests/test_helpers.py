from __future__ import annotations

import base64
from pathlib import Path

import pytest

from waha_fast_mcp import server


def test_jid_variants():
    assert server._jid({"_serialized": "549@c.us"}) == "549@c.us"
    assert server._jid({"id": "123@lid"}) == "123@lid"
    assert server._jid("456@g.us") == "456@g.us"
    assert server._jid(None) is None


def test_compact_chat_without_last_message():
    result = server._compact_chat({"id": "549@c.us", "name": "Ada"})

    assert result["id"] == "549@c.us"
    assert result["lastMessage"] is None


def test_file_payload_from_base64_defaults_mimetype():
    payload = server._file_payload(
        url=None,
        path=None,
        data_base64=base64.b64encode(b"data").decode(),
        filename=None,
        mimetype=None,
    )

    assert payload["mimetype"] == "application/octet-stream"
    assert base64.b64decode(payload["data"]) == b"data"


def test_file_payload_preserves_explicit_values():
    payload = server._file_payload(
        url="https://example.com/a.bin",
        path=None,
        data_base64=None,
        filename="a.bin",
        mimetype="application/x-custom",
    )

    assert payload == {
        "url": "https://example.com/a.bin",
        "filename": "a.bin",
        "mimetype": "application/x-custom",
    }


def test_file_payload_missing_path_raises(tmp_path: Path):
    missing = tmp_path / "missing.txt"

    with pytest.raises(ValueError, match="File not found"):
        server._file_payload(
            url=None,
            path=str(missing),
            data_base64=None,
            filename=None,
            mimetype=None,
        )
