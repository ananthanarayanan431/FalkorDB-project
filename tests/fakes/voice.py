import asyncio
import math
import struct

from knowledge_transfer.voice.providers import ProviderError


def tone(ms: int, amp: int = 8000, rate: int = 16000) -> bytes:
    n = rate * ms // 1000
    return struct.pack(f"<{n}h", *(int(amp * math.sin(2 * math.pi * 220 * i / rate)) for i in range(n)))


def silence(ms: int, rate: int = 16000) -> bytes:
    return b"\x00\x00" * (rate * ms // 1000)


class FakeTranscriber:
    """Returns the queued texts in order; 'ERR' raises a provider error."""

    def __init__(self, *texts: str):
        self.texts = list(texts)
        self.calls = 0

    async def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> str:
        self.calls += 1
        text = self.texts.pop(0) if self.texts else ""
        if text == "ERR":
            raise ProviderError("stt down")
        return text


class FakeSynthesizer:
    format = "mp3"

    def __init__(self):
        self.spoken: list[str] = []

    async def synthesize(self, text: str) -> bytes:
        self.spoken.append(text)
        await asyncio.sleep(0)
        return b"audio:" + text.encode()


class Outbox:
    def __init__(self):
        self.events: list[dict] = []
        self.clips: list[tuple[bytes, str]] = []

    async def event(self, payload):
        self.events.append(payload)

    async def audio(self, data, kind, fmt):
        self.clips.append((data, kind))

    def of(self, type_):
        return [e for e in self.events if e["type"] == type_]

    def said(self, role="agent"):
        return [e["text"] for e in self.of("transcript") if e["role"] == role]
