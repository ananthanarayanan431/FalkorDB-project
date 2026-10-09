import asyncio

from fakes.voice import FakeSynthesizer, FakeTranscriber, Outbox, tone

from knowledge_transfer.core.errors import InvalidState
from knowledge_transfer.services import gaps
from knowledge_transfer.voice.providers import VoiceProviders
from knowledge_transfer.voice.session import (
    NOT_HEARD,
    VOICE_SOURCE,
    State,
    VoiceSession,
)

GRACE = 0.05


async def make(interviews, *texts, grace=GRACE):
    session, _ = await interviews.start("ravi")
    out, tts, stt = Outbox(), FakeSynthesizer(), FakeTranscriber(*texts)
    voice = VoiceSession(interviews, session.id, VoiceProviders(stt, tts), out, grace_s=grace)
    await voice.start()
    await asyncio.sleep(0.01)  # let the speak task send its clips
    return voice, out, tts, session.id


async def settle(delay=GRACE * 6):
    await asyncio.sleep(delay)


async def finish_playback(voice):
    await voice.on_playback_done(voice._speak_id)


async def answers(graph, item):
    return (await graph.answers_for([item])).get(item, [])


async def test_start_speaks_the_question_then_listens_when_playback_ends(interviews):
    voice, out, _, _ = await make(interviews)
    assert voice.state is State.SPEAKING
    assert out.said()[0].startswith('On "')
    assert out.of("audio_end") and any(kind == "speech" for _, kind in out.clips)
    await voice.on_playback_done(999)  # stale id from an earlier speech: ignored
    assert voice.state is State.SPEAKING
    await finish_playback(voice)
    assert voice.state is State.LISTENING


async def test_speech_while_agent_talks_stops_it_and_is_saved_as_interrupted(seeded, interviews):
    voice, out, _, _ = await make(interviews, "the gateway blocks retries inside thirty minutes")
    item = voice._question["item_id"]
    await voice.on_speech_start()
    assert out.of("clear") and voice.state is State.LISTENING
    await voice.on_utterance(tone(500))
    await settle()
    saved = await answers(seeded, item)
    assert [a["text"] for a in saved] == ["the gateway blocks retries inside thirty minutes"]
    assert saved[0]["source"] == VOICE_SOURCE
    rows = (await seeded.graph.ro_query("MATCH (a:Answer) RETURN a.interrupted")).result_set
    assert rows == [[True]]


async def test_normal_answer_is_not_flagged_interrupted(seeded, interviews):
    voice, out, _, _ = await make(interviews, "an answer")
    await finish_playback(voice)
    await voice.on_speech_start()
    assert not out.of("clear")
    await voice.on_utterance(tone(500))
    await settle()
    rows = (await seeded.graph.ro_query("MATCH (a:Answer) RETURN a.interrupted")).result_set
    assert rows == [[False]]


async def test_pause_inside_grace_window_merges_into_one_answer(seeded, interviews):
    voice, out, _, _ = await make(interviews, "first part,", "and the second part", grace=0.3)
    item = voice._question["item_id"]
    await finish_playback(voice)
    await voice.on_utterance(tone(500))
    assert voice.state is State.PROCESSING
    await asyncio.sleep(0.1)
    await voice.on_speech_start()  # still talking: the pause was not the end
    assert voice.state is State.LISTENING
    await asyncio.sleep(0.4)  # keeps talking well past the original deadline: nothing saved yet
    assert await answers(seeded, item) == []
    await voice.on_utterance(tone(500))
    await settle(0.6)
    assert [a["text"] for a in await answers(seeded, item)] == ["first part, and the second part"]


async def test_speech_while_answer_is_being_saved_is_added_to_it(seeded, interviews):
    original = interviews.answer

    async def slow_answer(*a, **kw):
        await asyncio.sleep(0.2)
        return await original(*a, **kw)

    interviews.answer = slow_answer
    voice, out, _, sid = await make(interviews, "main answer", "oh and one more thing")
    item = voice._question["item_id"]
    await finish_playback(voice)
    await voice.on_utterance(tone(500))
    await asyncio.sleep(GRACE + 0.08)  # commit has started, the save is still running
    await voice.on_speech_start()
    await voice.on_utterance(tone(500))
    await settle(0.5)
    assert [a["text"] for a in await answers(seeded, item)] == ["main answer", "oh and one more thing"]
    actions = [t["action"] for t in await interviews.transcript(sid)]
    assert actions == ["answer", "amend"]
    assert any(e.get("amend") for e in out.of("transcript"))
    # the next question was still asked after saving
    assert voice._question["item_id"] != item


async def test_skip_command_skips_without_saving(seeded, interviews):
    voice, out, _, sid = await make(interviews, "skip")
    first = voice._question["item_id"]
    await finish_playback(voice)
    await voice.on_utterance(tone(500))
    await settle()
    assert await answers(seeded, first) == []
    assert voice._question["item_id"] != first
    assert first in (await interviews.get(sid)).skipped


async def test_repeat_command_asks_the_same_question_again(interviews):
    voice, out, tts, _ = await make(interviews, "repeat that")
    await finish_playback(voice)
    await voice.on_utterance(tone(500))
    await settle()
    said = out.said()
    assert len(said) == 2 and said[0] == said[1]


async def test_wait_command_stays_silent_and_listening(seeded, interviews):
    voice, out, _, _ = await make(interviews, "hold on")
    await finish_playback(voice)
    spoken_before = len(out.said())
    await voice.on_utterance(tone(500))
    await settle()
    assert voice.state is State.LISTENING and len(out.said()) == spoken_before


async def test_stop_command_says_goodbye_and_ends(interviews):
    voice, out, _, _ = await make(interviews, "that's enough")
    await finish_playback(voice)
    await voice.on_utterance(tone(500))
    await settle()
    assert out.of("ended") == [{"type": "ended", "reason": "complete"}]
    assert voice.state is State.ENDED


async def test_blip_is_ignored_but_unintelligible_audio_asks_again(seeded, interviews):
    voice, out, _, _ = await make(interviews, "")
    await finish_playback(voice)
    await voice.on_utterance(b"")  # VAD reported a too-short sound
    await settle()
    assert NOT_HEARD not in out.said() and voice.state is State.LISTENING
    await voice.on_utterance(tone(500))  # real audio, STT returns nothing
    await settle()
    assert NOT_HEARD in out.said()


async def test_transcription_failure_is_reported_and_nothing_is_saved(seeded, interviews):
    voice, out, _, _ = await make(interviews, "ERR")
    item = voice._question["item_id"]
    await finish_playback(voice)
    await voice.on_utterance(tone(500))
    await settle()
    assert out.of("error") and voice.state is State.LISTENING
    assert await answers(seeded, item) == []


async def test_acknowledgement_plays_before_the_answer_is_saved(interviews):
    voice, out, _, _ = await make(interviews, "an answer")
    await finish_playback(voice)
    await voice.on_utterance(tone(500))
    await settle()
    assert any(kind == "ack" for _, kind in out.clips)


async def test_interview_ends_when_every_gap_is_answered(seeded, interviews):
    n = len(await gaps.open_gaps(seeded, "ravi"))
    voice, out, _, _ = await make(interviews, *(["because"] * (n + 5)))
    for _ in range(n + 5):
        if voice.state is State.ENDED:
            break
        await finish_playback(voice)
        await voice.on_utterance(tone(500))
        await settle(GRACE * 8)
    assert out.of("ended") and (await gaps.coverage(seeded, "ravi"))["percent"] == 100.0


async def test_close_cancels_background_work(interviews):
    voice, *_ = await make(interviews, "x")
    await voice.on_utterance(tone(500))
    await voice.close()
    assert voice.state is State.ENDED
    await voice.on_utterance(tone(500))  # ignored after close


async def test_conflict_re_asks_the_current_question(seeded, interviews):
    original_skip = interviews.skip

    async def conflicting_answer(sid, *a, **kw):
        await original_skip(sid)  # another client moved the interview on first
        raise InvalidState("Interview was updated by another request; fetch it and retry")

    interviews.answer = conflicting_answer
    voice, out, _, sid = await make(interviews, "an answer")
    first = voice._question["item_id"]
    await finish_playback(voice)
    await voice.on_utterance(tone(500))
    await settle()
    current = (await interviews.get(sid)).current
    assert out.of("error") and current.item_id != first
    assert voice._question == current.to_dict()
    assert out.said()[-1] == current.text  # re-asked, so the next answer is saved against it
