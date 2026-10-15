"""Spoken interview over a WebSocket.

Client -> server: binary frames of 16 kHz mono PCM16 microphone audio, and JSON
`{"type": "playback_done", "id": n}` once the browser has played everything for speech n.
Server -> client: JSON events (state, transcript, saved, clear, audio_end, error, ended); each
audio clip is a JSON `{"type": "audio", "kind", "format"}` message followed by a binary frame.

Browsers do not apply the same-origin policy to WebSockets, so the handshake's Origin is
checked against ALLOWED_ORIGINS before the connection is accepted (cross-site WebSocket
hijacking would otherwise let any web page start a voice session and spend provider credit).
"""
import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.responses import HTMLResponse

from knowledge_transfer.core.config import get_settings
from knowledge_transfer.core.errors import NotFound
from knowledge_transfer.voice.session import VoiceSession

logger = logging.getLogger(__name__)
router = APIRouter(tags=["voice"])

DEMO_PAGE = Path(__file__).resolve().parents[3] / "voice" / "static" / "demo.html"

# The browser sends 128-sample frames (256 bytes); anything near these limits is abuse.
MAX_AUDIO_FRAME_BYTES = 64 * 1024
MAX_CONTROL_MESSAGE_CHARS = 1024


class WebSocketOutbox:
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self._lock = asyncio.Lock()  # a JSON header and its audio frame must stay together

    async def event(self, payload: dict) -> None:
        async with self._lock:
            await self.ws.send_json(payload)

    async def audio(self, data: bytes, kind: str, fmt: str) -> None:
        async with self._lock:
            await self.ws.send_json({"type": "audio", "kind": kind, "format": fmt})
            await self.ws.send_bytes(data)


def origin_allowed(origin: str | None) -> bool:
    """Browsers always send Origin on a WebSocket handshake; other clients may omit it."""
    return origin is None or origin in get_settings().allowed_origins


@router.get("/voice-demo", include_in_schema=False)
async def voice_demo() -> HTMLResponse:
    """A bare test page for the voice socket. Not served in production."""
    if get_settings().is_production:
        raise NotFound("Not found")
    return HTMLResponse(DEMO_PAGE.read_text())


@router.websocket("/interviews/{interview_id}/voice")
async def voice_interview(ws: WebSocket, interview_id: str) -> None:
    if not origin_allowed(ws.headers.get("origin")):
        logger.warning("Rejected voice socket from origin %r", ws.headers.get("origin"))
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)  # before accept: handshake gets 403
        return
    services = ws.app.state.services
    await ws.accept()
    out = WebSocketOutbox(ws)
    if services.voice is None:
        await out.event({"type": "error", "message": "Voice is not configured (set OPENROUTER_API_KEY)"})
        await ws.close(code=status.WS_1011_INTERNAL_ERROR)
        return
    grace = get_settings().voice_grace_s  # pause allowed before an answer is saved
    session = VoiceSession(services.interviews, interview_id, services.voice, out, grace_s=grace)
    try:
        await session.start()
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if (audio := msg.get("bytes")) is not None:
                if len(audio) > MAX_AUDIO_FRAME_BYTES:
                    await ws.close(code=status.WS_1009_MESSAGE_TOO_BIG)
                    break
                await session.on_audio(audio)
            elif text := msg.get("text"):
                if len(text) > MAX_CONTROL_MESSAGE_CHARS:
                    await ws.close(code=status.WS_1009_MESSAGE_TOO_BIG)
                    break
                try:
                    data = json.loads(text)
                    speak_id = int(data["id"]) if data.get("type") == "playback_done" else None
                except (ValueError, TypeError, KeyError, AttributeError):
                    logger.warning("Ignoring malformed voice control message")
                    continue
                if speak_id is not None:
                    await session.on_playback_done(speak_id)
    except NotFound as e:
        await out.event({"type": "error", "message": e.message})
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Voice socket failed")
        await ws.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        await session.close()
