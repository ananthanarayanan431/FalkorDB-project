import asyncio
import json
from types import SimpleNamespace

import pytest
from fakes.voice import FakeSynthesizer, FakeTranscriber, silence, tone

from knowledge_transfer.api import Services
from knowledge_transfer.api.v1.routes.voice import voice_interview
from knowledge_transfer.voice.providers import VoiceProviders


class FakeWebSocket:
    """Just enough of Starlette's WebSocket, driven from the test."""

    def __init__(self, services):
        self.app = SimpleNamespace(state=SimpleNamespace(services=services))
        self.incoming: asyncio.Queue = asyncio.Queue()
        self.sent: list = []
        self.accepted = False
        self.closed_with: int | None = None

    async def accept(self):
        self.accepted = True

    async def receive(self):
        return await self.incoming.get()

    async def send_json(self, data):
        self.sent.append(data)

    async def send_bytes(self, data):
        self.sent.append(data)

    async def close(self, code=1000):
        self.closed_with = code

    def push_audio(self, pcm):
        self.incoming.put_nowait({"type": "websocket.receive", "bytes": pcm})

    def push_json(self, data):
        self.incoming.put_nowait({"type": "websocket.receive", "text": json.dumps(data)})

    def disconnect(self):
        self.incoming.put_nowait({"type": "websocket.disconnect"})

    def events(self, type_):
        return [m for m in self.sent if isinstance(m, dict) and m["type"] == type_]


async def wait_for(cond, timeout=3.0):
    loop = asyncio.get_running_loop()
    end = loop.time() + timeout
    while not cond():
        assert loop.time() < end, "timed out"
        await asyncio.sleep(0.01)


@pytest.fixture(autouse=True)
def fast_grace(monkeypatch):
    monkeypatch.setenv("VOICE_GRACE_S", "0.05")


async def test_spoken_turn_over_the_socket(seeded, assistant, db, interviews):
    stt = FakeTranscriber("because the gateway window is thirty minutes")
    services = Services(seeded, assistant, db, VoiceProviders(stt, FakeSynthesizer()))
    session, q = await services.interviews.start("ravi")
    ws = FakeWebSocket(services)
    task = asyncio.create_task(voice_interview(ws, session.id))

    await wait_for(lambda: ws.events("audio_end"))
    # a JSON header is always followed by its audio frame
    i = next(i for i, m in enumerate(ws.sent) if isinstance(m, dict) and m["type"] == "audio")
    assert ws.sent[i]["format"] == "mp3" and isinstance(ws.sent[i + 1], bytes)

    # malformed control messages are ignored, not fatal
    ws.incoming.put_nowait({"type": "websocket.receive", "text": "not json"})
    ws.push_json([1, 2])
    ws.push_json({"type": "playback_done", "id": "abc"})
    ws.push_json({"type": "playback_done", "id": ws.events("audio_end")[0]["id"]})
    await wait_for(lambda: ws.events("state") and ws.events("state")[-1]["state"] == "listening")

    # real VAD path: 1 s of speech then 1.5 s of silence, in 100 ms chunks
    pcm = silence(300) + tone(1000) + silence(1500)
    for i in range(0, len(pcm), 3200):
        ws.push_audio(pcm[i:i + 3200])
    await wait_for(lambda: ws.events("saved"))
    assert ws.events("saved")[0]["item_id"] == q.item_id
    assert (await interviews.get(session.id)).turns == 1
    await wait_for(lambda: len(ws.events("audio_end")) == 2)  # the next question was spoken

    ws.disconnect()
    await asyncio.wait_for(task, 2)
    assert ws.closed_with is None


async def test_voice_disabled_without_providers(seeded, assistant, db):
    ws = FakeWebSocket(Services(seeded, assistant, db))
    await voice_interview(ws, "whatever")
    assert ws.events("error") and ws.closed_with == 1011


async def test_unknown_interview_closes_with_error(seeded, assistant, db):
    services = Services(seeded, assistant, db, VoiceProviders(FakeTranscriber(), FakeSynthesizer()))
    ws = FakeWebSocket(services)
    await voice_interview(ws, "nope")
    assert "Unknown interview" in ws.events("error")[0]["message"] and ws.closed_with == 1008
