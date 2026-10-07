"""Tests for the processing-events SSE router keepalive behavior."""

from __future__ import annotations

import pytest

from shared.presentation.api import processing_events_router as router_module


class _Request:
    """Minimal Request stub: connected for the first two polls, then gone."""

    def __init__(self, connected_polls: int = 2):
        self._remaining = connected_polls

    async def is_disconnected(self) -> bool:
        if self._remaining > 0:
            self._remaining -= 1
            return False
        return True


async def _one_chunk(*args, **kwargs):
    yield "event: execution.created\ndata: {}\n\n"


@pytest.mark.asyncio
async def test_stream_starts_with_connected_comment_and_keepalive(monkeypatch):
    """First frame must be `: connected`; idle loop must yield `: ping`."""
    monkeypatch.setattr(router_module, "_validate_token", lambda token: "user-1")
    monkeypatch.setattr(router_module, "stream_pattern_for_user", _one_chunk)
    monkeypatch.setattr(router_module, "SSE_KEEPALIVE_SECONDS", 0)

    response = await router_module.processing_events(_Request(), token="tok")
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)
        if len(chunks) >= 4:
            break

    assert chunks[0] == ": connected\n\n"
    assert chunks[1].startswith("event: execution.created")
    assert any(c == ": ping\n\n" for c in chunks[2:])


@pytest.mark.asyncio
async def test_stream_disables_proxy_transforms(monkeypatch):
    """The stream must forbid proxy compression (`no-transform`).

    The Next.js standalone rewrite proxy compresses proxied responses for
    gzip-accepting browsers, which buffers SSE frames and breaks live updates.
    """
    monkeypatch.setattr(router_module, "_validate_token", lambda token: "user-1")
    monkeypatch.setattr(router_module, "stream_pattern_for_user", _one_chunk)

    response = await router_module.processing_events(_Request(), token="tok")

    assert response.media_type == "text/event-stream"
    assert "no-transform" in response.headers["cache-control"]
    assert response.headers["x-accel-buffering"] == "no"
