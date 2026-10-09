import base64
import json

import httpx
import pytest
from fakes.voice import silence, tone

from knowledge_transfer.voice.commands import parse_command
from knowledge_transfer.voice.providers import (
    OpenRouterSynthesizer,
    OpenRouterTranscriber,
    ProviderError,
    pcm_to_wav,
    split_sentences,
)
from knowledge_transfer.voice.vad import EnergyVad


def feed(vad, pcm):
    return [e.kind for e in vad.feed(pcm)], vad


def test_vad_detects_start_then_utterance_after_silence():
    vad = EnergyVad()
    kinds, _ = feed(vad, silence(500) + tone(1000))
    assert kinds == ["speech_start"]
    events = vad.feed(silence(1400))
    assert [e.kind for e in events] == ["utterance"]
    # includes pre-roll and the speech itself: at least the 1 s of tone
    assert len(events[0].pcm) >= 16000 * 2


def test_vad_ignores_short_noise():
    vad = EnergyVad()
    assert vad.feed(silence(500) + tone(100) + silence(2000)) == []


def test_vad_tolerates_short_pauses_inside_speech():
    vad = EnergyVad()
    vad.feed(silence(300))
    events = vad.feed(tone(500) + silence(400) + tone(500) + silence(1400))
    assert [e.kind for e in events] == ["speech_start", "utterance"]


def test_vad_handles_arbitrary_chunk_sizes():
    vad = EnergyVad()
    pcm = silence(300) + tone(800) + silence(1500)
    kinds = []
    for i in range(0, len(pcm), 777):  # not a multiple of the frame size
        kinds += [e.kind for e in vad.feed(pcm[i:i + 777])]
    assert kinds == ["speech_start", "utterance"]


def test_vad_adapts_to_a_noisy_room():
    vad = EnergyVad()
    vad.feed(tone(2000, amp=200))  # steady hiss below the floor: never speech
    assert not vad.in_speech
    assert [e.kind for e in vad.feed(tone(800, amp=9000))] == ["speech_start"]


@pytest.mark.parametrize("text,expected", [
    ("Skip.", "skip"), ("next question", "skip"), ("Repeat that", "repeat"),
    ("hold on", "wait"), ("Okay, that's enough", None), ("that's enough", "stop"),
    ("We should skip the retry logic because it is deprecated", None), ("", None),
])
def test_parse_command(text, expected):
    assert parse_command(text) == expected


def test_split_sentences():
    assert split_sentences("One. Two! Three?") == ["One.", "Two!", "Three?"]
    long = "word " * 100
    chunks = split_sentences(long, max_chars=50)
    assert all(len(c) <= 50 for c in chunks) and " ".join(chunks).split() == long.split()


def test_pcm_to_wav_header():
    wav = pcm_to_wav(tone(100))
    assert wav[:4] == b"RIFF" and wav[8:12] == b"WAVE"


def _client(handler):
    return httpx.AsyncClient(base_url="https://x/api/v1", transport=httpx.MockTransport(handler))


async def test_transcriber_sends_wav_and_returns_text():
    seen = {}

    def handler(req):
        seen.update(json.loads(req.content), path=req.url.path)
        return httpx.Response(200, json={"text": " hello there "})

    stt = OpenRouterTranscriber("k", client=_client(handler))
    assert await stt.transcribe(tone(100)) == "hello there"
    assert seen["model"] == "deepgram/nova-3" and seen["path"].endswith("/audio/transcriptions")
    assert base64.b64decode(seen["input_audio"]["data"])[:4] == b"RIFF"
    assert seen["input_audio"]["format"] == "wav"


async def test_synthesizer_requests_mp3_with_voice():
    seen = {}

    def handler(req):
        seen.update(json.loads(req.content), path=req.url.path)
        return httpx.Response(200, content=b"MP3DATA")

    tts = OpenRouterSynthesizer("k", client=_client(handler))
    assert await tts.synthesize("hi") == b"MP3DATA"
    assert seen["model"] == "deepgram/aura-2" and seen["voice"] == "aura-2-thalia-en"
    assert seen["response_format"] == "mp3" and seen["path"].endswith("/audio/speech")


async def test_provider_http_errors_become_provider_error():
    stt = OpenRouterTranscriber("k", client=_client(lambda r: httpx.Response(500)))
    with pytest.raises(ProviderError):
        await stt.transcribe(tone(100))
