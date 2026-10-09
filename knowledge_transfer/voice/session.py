"""Voice front end for an interview. Transport-agnostic: audio comes in through
`on_audio`, everything going out goes through an `Outbox`.

States
  SPEAKING    the agent is talking (or its audio is still playing in the browser)
  LISTENING   waiting for the leaver
  PROCESSING  the leaver finished; a short grace window runs, then the answer is saved

Interruptions
  speech while SPEAKING          stop talking at once (the browser is told to drop its audio
                                 queue) and take what is said as the answer, flagged
                                 `interrupted`
  speech during the grace window the pause was not the end: the earlier words and the new
                                 ones are saved together as one answer
  speech while the answer is     it is saved as an addition (`amend`) to that answer
  being saved
  speech after the next question starts playing is the answer to that question
Short spoken commands (skip, repeat, wait, stop) are checked before an utterance is saved.
"""
import asyncio
import logging
from enum import StrEnum
from typing import Protocol

from knowledge_transfer.services.interview import InterviewService
from knowledge_transfer.voice.commands import parse_command
from knowledge_transfer.voice.providers import (
    ProviderError,
    VoiceProviders,
    split_sentences,
)
from knowledge_transfer.voice.vad import EnergyVad

logger = logging.getLogger(__name__)

VOICE_SOURCE = "interview-voice"
ACK = "Okay."
NOT_HEARD = "Sorry, I didn't catch that. Could you say it again?"
DONE = "That covers everything I wanted to ask. Thank you, this will make the handover much easier."
STOPPED = "Okay, we can stop here. Thank you, and you can come back to continue any time."


class State(StrEnum):
    SPEAKING = "speaking"
    LISTENING = "listening"
    PROCESSING = "processing"
    ENDED = "ended"


class Outbox(Protocol):
    async def event(self, payload: dict) -> None: ...
    async def audio(self, data: bytes, kind: str, fmt: str) -> None: ...


class VoiceSession:
    def __init__(self, interviews: InterviewService, interview_id: str, providers: VoiceProviders,
                 out: Outbox, vad: EnergyVad | None = None, grace_s: float = 0.8):
        self.interviews = interviews
        self.interview_id = interview_id
        self.stt = providers.transcriber
        self.tts = providers.synthesizer
        self.out = out
        self.vad = vad or EnergyVad()
        self.grace_s = grace_s
        self.state = State.LISTENING
        self._question: dict | None = None
        self._speak_task: asyncio.Task | None = None
        self._speak_id = 0
        self._grace_task: asyncio.Task | None = None
        self._pending: list[asyncio.Task[str]] = []  # transcriptions awaiting commit
        self._late: list[asyncio.Task[str]] = []  # spoken while the answer was being saved
        self._committing = False
        self._interrupted = False
        self._ack: bytes | None = None
        self._heard_audio = False  # the VAD passed real audio since the last commit

    # ---- lifecycle ---------------------------------------------------------

    async def start(self) -> None:
        session = await self.interviews.get(self.interview_id)
        await self._set(State.LISTENING)
        try:
            self._ack = await self.tts.synthesize(ACK)
        except ProviderError:
            logger.warning("Could not pre-synthesise the acknowledgement", exc_info=True)
        if session.current is None:
            await self._say(DONE, end=True)
        else:
            self._question = session.current.to_dict()
            await self._ask(self._question)

    async def close(self) -> None:
        self.state = State.ENDED
        for task in (self._speak_task, self._grace_task, *self._pending, *self._late):
            if task and not task.done():
                task.cancel()

    # ---- input -------------------------------------------------------------

    async def on_audio(self, pcm: bytes) -> None:
        if self.state is State.ENDED:
            return
        for ev in self.vad.feed(pcm):
            if ev.kind == "speech_start":
                await self.on_speech_start()
            else:
                await self.on_utterance(ev.pcm)

    async def on_speech_start(self) -> None:
        if self.state is State.SPEAKING:
            await self._barge_in()
        elif self._committing:
            pass  # saved as an amendment when the utterance ends
        elif self._grace_task and not self._grace_task.done():
            self._grace_task.cancel()  # the pause was not the end of the answer
            await self._set(State.LISTENING)

    async def on_utterance(self, pcm: bytes) -> None:
        """One complete stretch of speech (the leaver stopped talking)."""
        if self.state is State.ENDED:
            return
        task = asyncio.create_task(self._transcribe(pcm))
        self._heard_audio = self._heard_audio or bool(pcm)
        if self._committing:
            self._late.append(task)
            return
        self._pending.append(task)
        await self._set(State.PROCESSING)
        self._grace_task = asyncio.create_task(self._grace())

    async def on_playback_done(self, speak_id: int) -> None:
        """The browser finished playing everything for speech number `speak_id`."""
        if (self.state is State.SPEAKING and speak_id == self._speak_id
                and self._speak_task and self._speak_task.done()):
            await self._set(State.LISTENING)

    # ---- interruption ------------------------------------------------------

    async def _barge_in(self) -> None:
        if self._speak_task and not self._speak_task.done():
            self._speak_task.cancel()
        await self.out.event({"type": "clear"})
        self._interrupted = True
        await self._set(State.LISTENING)

    # ---- speaking ----------------------------------------------------------

    async def _ask(self, question: dict) -> None:
        await self._say(question["text"], meta={"item_id": question["item_id"],
                                                "reasons": question["reasons"]})

    async def _say(self, text: str, end: bool = False, meta: dict | None = None) -> None:
        if self._speak_task and not self._speak_task.done():
            self._speak_task.cancel()
        self._speak_id += 1
        self._interrupted = False
        await self._set(State.SPEAKING)
        await self.out.event({"type": "transcript", "role": "agent", "text": text, **(meta or {})})
        self._speak_task = asyncio.create_task(self._speak(text, self._speak_id, end))

    async def _speak(self, text: str, speak_id: int, end: bool) -> None:
        try:
            for sentence in split_sentences(text):
                await self.out.audio(await self.tts.synthesize(sentence), "speech", self.tts.format)
            await self.out.event({"type": "audio_end", "id": speak_id})
            if end:
                await self.out.event({"type": "ended", "reason": "complete"})
                self.state = State.ENDED
        except asyncio.CancelledError:
            raise
        except ProviderError as e:
            await self._fail(f"Could not speak: {e}")

    # ---- answering ---------------------------------------------------------

    async def _transcribe(self, pcm: bytes) -> str:
        return await self.stt.transcribe(pcm) if pcm else ""

    async def _grace(self) -> None:
        await asyncio.sleep(self.grace_s)
        await self._commit()

    async def _commit(self) -> None:
        self._committing = True  # no await before this: speech can no longer cancel the grace timer
        pending, self._pending = self._pending, []
        heard_audio, self._heard_audio = self._heard_audio, False
        try:
            results = await asyncio.gather(*pending, return_exceptions=True)
            if errors := [r for r in results if isinstance(r, Exception)]:
                await self._fail(f"Could not transcribe: {errors[0]}")
                return
            text = " ".join(r for r in results if r).strip()
            if not text:
                # A too-short blip (empty pcm) is ignored; real audio that yields no words
                # means the speaker should be asked to repeat.
                if heard_audio:
                    await self._say(NOT_HEARD)
                else:
                    await self._set(State.LISTENING)
                return
            await self.out.event({"type": "transcript", "role": "user", "text": text})
            await self._handle(text)
        except Exception as e:  # keep the interview alive; the leaver can just speak again
            logger.exception("Voice turn failed")
            await self._fail(f"Something went wrong: {e}")
        finally:
            self._committing = False
            self._interrupted = False

    async def _handle(self, text: str) -> None:
        command = parse_command(text)
        if command == "wait":
            await self._set(State.LISTENING)
        elif command == "repeat" and self._question:
            await self._ask(self._question)
        elif command == "stop":
            await self._say(STOPPED, end=True)
        elif command == "skip":
            await self._advance((await self.interviews.skip(self.interview_id))["next_question"])
        else:
            await self._answer(text)

    async def _answer(self, text: str) -> None:
        answered = self._question
        if self._ack:
            await self.out.audio(self._ack, "ack", self.tts.format)
        result = await asyncio.shield(self.interviews.answer(
            self.interview_id, text, source=VOICE_SOURCE, interrupted=self._interrupted))
        await self.out.event({"type": "saved", "item_id": result["stored_for"],
                              "answer_type": result["answer_type"], "new_items": result["new_items"]})
        await self._add_late_speech(answered)
        await self._advance(result["next_question"])

    async def _add_late_speech(self, answered: dict | None) -> None:
        late, self._late = self._late, []
        self._heard_audio = False
        texts = [t for t in await asyncio.gather(*late, return_exceptions=True)
                 if isinstance(t, str) and t]
        if not (texts and answered):
            return
        text = " ".join(texts)
        await self.out.event({"type": "transcript", "role": "user", "text": text, "amend": True})
        await self.interviews.amend(self.interview_id, answered["item_id"], answered["text"],
                                    text, source=VOICE_SOURCE)

    async def _advance(self, next_question: dict | None) -> None:
        self._question = next_question
        if next_question is None:
            await self._say(DONE, end=True)
        else:
            await self._ask(next_question)

    # ---- helpers -----------------------------------------------------------

    async def _set(self, state: State) -> None:
        if self.state is not state and self.state is not State.ENDED:
            self.state = state
            await self.out.event({"type": "state", "state": state.value})

    async def _fail(self, message: str) -> None:
        await self.out.event({"type": "error", "message": message})
        await self._set(State.LISTENING)
