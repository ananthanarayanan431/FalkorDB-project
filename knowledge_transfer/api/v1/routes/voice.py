"""Spoken interview over a WebSocket.

Client -> server: binary frames of 16 kHz mono PCM16 microphone audio, and JSON
`{"type": "playback_done", "id": n}` once the browser has played everything for speech n.
Server -> client: JSON events (state, transcript, saved, clear, audio_end, error, ended); each
audio clip is a JSON `{"type": "audio", "kind", "format"}` message followed by a binary frame.
"""
import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from knowledge_transfer.core.config import get_settings
from knowledge_transfer.core.errors import NotFound
from knowledge_transfer.voice.session import VoiceSession

logger = logging.getLogger(__name__)
router = APIRouter(tags=["voice"])

DEMO_PAGE = Path(__file__).resolve().parents[3] / "voice" / "static" / "demo.html"


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


@router.get("/voice-demo", include_in_schema=False)
async def voice_demo() -> HTMLResponse:
    return HTMLResponse(DEMO_PAGE.read_text())


@router.websocket("/interviews/{interview_id}/voice")
async def voice_interview(ws: WebSocket, interview_id: str) -> None:
    services = ws.app.state.services
    await ws.accept()
    out = WebSocketOutbox(ws)
    if services.voice is None:
        await out.event({"type": "error", "message": "Voice is not configured (set OPENROUTER_API_KEY)"})
        await ws.close(code=1011)
        return
    grace = get_settings().voice_grace_s  # pause allowed before an answer is saved
    session = VoiceSession(services.interviews, interview_id, services.voice, out, grace_s=grace)
    try:
        await session.start()
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if msg.get("bytes") is not None:
                await session.on_audio(msg["bytes"])
            elif msg.get("text"):
                try:
                    data = json.loads(msg["text"])
                    speak_id = int(data["id"]) if data.get("type") == "playback_done" else None
                except (ValueError, TypeError, KeyError, AttributeError):
                    logger.warning("Ignoring malformed voice control message")
                    continue
                if speak_id is not None:
                    await session.on_playback_done(speak_id)
    except NotFound as e:
        await out.event({"type": "error", "message": str(e)})
        await ws.close(code=1008)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Voice socket failed")
        await ws.close(code=1011)
    finally:
        await session.close()
