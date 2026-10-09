"""Speech-to-text and text-to-speech through OpenRouter (one API key for everything).

Defaults: Deepgram Nova-3 for transcription and Deepgram Aura-2 for synthesis. Both
OpenRouter endpoints are request/response, not live streams, so the session sends one
utterance (or one sentence) per call.
"""
import base64
import io
import re
import wave
from typing import Protocol

import httpx

from knowledge_transfer.core.config import get_settings

BASE_URL = "https://openrouter.ai/api/v1"


class ProviderError(RuntimeError):
    """A speech provider call failed."""


class Transcriber(Protocol):
    async def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> str: ...


class Synthesizer(Protocol):
    format: str  # audio container the browser should decode, e.g. "mp3"

    async def synthesize(self, text: str) -> bytes: ...


def pcm_to_wav(pcm: bytes, sample_rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


class _OpenRouter:
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None):
        self._client = client or httpx.AsyncClient(
            base_url=BASE_URL, timeout=30, headers={"Authorization": f"Bearer {api_key}"}
        )

    async def _post(self, path: str, payload: dict) -> httpx.Response:
        try:
            resp = await self._client.post(path, json=payload)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise ProviderError(f"{path} failed: {e}") from e
        return resp

    async def aclose(self) -> None:
        await self._client.aclose()


class OpenRouterTranscriber(_OpenRouter):
    def __init__(self, api_key: str, model: str | None = None, **kw):
        super().__init__(api_key, **kw)
        self.model = model or get_settings().stt_model

    async def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> str:
        if not pcm:
            return ""
        audio = base64.b64encode(pcm_to_wav(pcm, sample_rate)).decode()
        resp = await self._post("/audio/transcriptions", {
            "model": self.model, "input_audio": {"data": audio, "format": "wav"},
        })
        return str(resp.json().get("text", "")).strip()


class OpenRouterSynthesizer(_OpenRouter):
    format = "mp3"

    def __init__(self, api_key: str, model: str | None = None, voice: str | None = None, **kw):
        super().__init__(api_key, **kw)
        self.model = model or get_settings().tts_model
        self.voice = voice or get_settings().tts_voice

    async def synthesize(self, text: str) -> bytes:
        resp = await self._post("/audio/speech", {
            "model": self.model, "input": text, "voice": self.voice, "response_format": self.format,
        })
        return resp.content


class VoiceProviders:
    def __init__(self, transcriber: Transcriber, synthesizer: Synthesizer):
        self.transcriber = transcriber
        self.synthesizer = synthesizer

    @classmethod
    def from_env(cls) -> "VoiceProviders | None":
        """None when OPENROUTER_API_KEY is not set (voice then answers 503)."""
        if not (key := get_settings().openrouter_api_key):
            return None
        return cls(OpenRouterTranscriber(key), OpenRouterSynthesizer(key))

    async def aclose(self) -> None:
        for p in (self.transcriber, self.synthesizer):
            if close := getattr(p, "aclose", None):
                await close()


_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str, max_chars: int = 220) -> list[str]:
    """Sentence-sized chunks, so the first one can be played while the rest are synthesised."""
    out: list[str] = []
    for part in _SENTENCE.split(text.strip()):
        while len(part) > max_chars:
            cut = part.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            out.append(part[:cut].strip())
            part = part[cut:].strip()
        if part:
            out.append(part)
    return out
