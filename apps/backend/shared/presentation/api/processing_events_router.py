"""Global processing-events SSE router.

Serves a single Server-Sent Event stream at /events/processing that
forwards ProcessingExecution lifecycle events to the frontend.

Authentication is via a ``token`` query parameter (EventSource does not
support custom headers). The JWT is validated and the stream is scoped to
the authenticated user's events only.

Registered directly on the app (no /api prefix) — matches the frontend
hook useProcessingEvents() which subscribes to SSE_URL='/events/processing'.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from shared.infrastructure.events.processing_events import CHANNEL_PATTERN
from shared.infrastructure.events.sse import stream_pattern_for_user
from shared.infrastructure.config.app_config import SSE_KEEPALIVE_SECONDS

router = APIRouter()


def _validate_token(token: str) -> str:
    """Validate JWT and return the user_id. Raises HTTPException on failure."""
    from auth.application.auth_service import AuthService
    from auth.infrastructure.user_repository import SQLAlchemyUserRepository
    from shared.infrastructure.database.session import get_session_sync

    session = get_session_sync()
    try:
        repo = SQLAlchemyUserRepository(session)
        auth_service = AuthService(repo)
        user = auth_service.verify_token(token)
        return user.id
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    finally:
        session.close()


@router.get("/processing")
async def processing_events(request: Request, token: str = Query(...)):
    user_id = _validate_token(token)

    async def event_stream():
        # Initial comment keeps intermediaries from buffering the stream and
        # confirms the connection without emitting a domain event.
        yield ": connected\n\n"
        async for chunk in stream_pattern_for_user(CHANNEL_PATTERN, user_id):
            if await request.is_disconnected():
                break
            yield chunk
        while not await request.is_disconnected():
            # Periodic SSE comment as keepalive; EventSource ignores comments
            # but proxies reset their idle timeout on any bytes.
            yield ": ping\n\n"
            await asyncio.sleep(SSE_KEEPALIVE_SECONDS)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        # `no-transform` forbids intermediaries (e.g. the Next.js standalone
        # rewrite proxy) from compressing the stream: compression buffers SSE
        # frames, so gzip-accepting browsers would receive nothing live.
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
