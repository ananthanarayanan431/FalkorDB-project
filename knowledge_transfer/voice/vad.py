"""Voice activity detection on 16 kHz mono PCM16, with no dependencies.

Energy based: a frame is voiced when its RMS is well above a noise floor that adapts to the
room. The speaker must stay voiced for `start_ms` before `speech_start` fires, so coughs and
clicks do not count. After `end_silence_ms` of silence the whole utterance (including a
little audio from before speech started, so first words are not clipped) is returned.

Swap in a model-based VAD (for example Silero) by implementing the same `feed()`.
"""
import array
import math
from dataclasses import dataclass


@dataclass
class VadEvent:
    kind: str  # "speech_start" | "utterance"
    pcm: bytes = b""


class EnergyVad:
    def __init__(self, sample_rate: int = 16000, frame_ms: int = 20, start_ms: int = 300,
                 end_silence_ms: int = 1200, preroll_ms: int = 300, min_utterance_ms: int = 400,
                 max_utterance_s: float = 60.0, min_rms: float = 350.0, noise_factor: float = 3.0):
        self.frame_ms = frame_ms
        self.frame_bytes = sample_rate * frame_ms // 1000 * 2
        self.start_frames = start_ms // frame_ms
        self.end_frames = end_silence_ms // frame_ms
        self.preroll_frames = preroll_ms // frame_ms
        self.min_utterance_frames = min_utterance_ms // frame_ms
        self.max_frames = int(max_utterance_s * 1000 / frame_ms)
        self.min_rms = min_rms
        self.noise_factor = noise_factor
        self.reset()

    def reset(self) -> None:
        self._buf = b""
        self._noise = 0.0
        self._preroll: list[bytes] = []
        self._run = 0  # consecutive voiced frames while idle
        self._gap = 0  # unvoiced frames tolerated inside that run
        self._run_frames: list[bytes] = []
        self._utt: list[bytes] = []
        self._silence = 0
        self.in_speech = False

    @staticmethod
    def _rms(frame: bytes) -> float:
        samples = array.array("h")
        samples.frombytes(frame)
        return math.sqrt(sum(s * s for s in samples) / len(samples)) if samples else 0.0

    def feed(self, pcm: bytes) -> list[VadEvent]:
        self._buf += pcm
        events: list[VadEvent] = []
        while len(self._buf) >= self.frame_bytes:
            frame, self._buf = self._buf[: self.frame_bytes], self._buf[self.frame_bytes:]
            events += self._frame(frame)
        return events

    def _voiced(self, frame: bytes) -> bool:
        rms = self._rms(frame)
        threshold = max(self.min_rms, self._noise * self.noise_factor)
        voiced = rms >= threshold
        if not voiced and not self.in_speech:
            self._noise = rms if self._noise == 0.0 else 0.95 * self._noise + 0.05 * rms
        return voiced

    def _frame(self, frame: bytes) -> list[VadEvent]:
        voiced = self._voiced(frame)
        if not self.in_speech:
            return self._idle(frame, voiced)
        self._utt.append(frame)
        self._silence = 0 if voiced else self._silence + 1
        if self._silence >= self.end_frames or len(self._utt) >= self.max_frames:
            return [self._finish()]
        return []

    def _idle(self, frame: bytes, voiced: bool) -> list[VadEvent]:
        if voiced:
            self._run += 1
            self._gap = 0
            self._run_frames.append(frame)
            if self._run >= self.start_frames:
                self.in_speech = True
                self._utt = self._preroll + self._run_frames
                self._silence = 0
                self._preroll, self._run_frames, self._run = [], [], 0
                return [VadEvent("speech_start")]
            return []
        if self._run:
            self._gap += 1  # brief dips between syllables are allowed
            self._run_frames.append(frame)
            if self._gap > 3:
                self._preroll = (self._preroll + self._run_frames)[-self.preroll_frames:]
                self._run_frames, self._run, self._gap = [], 0, 0
            return []
        self._preroll = (self._preroll + [frame])[-self.preroll_frames:]
        return []

    def _finish(self) -> VadEvent:
        frames = self._utt
        self._utt, self._silence, self.in_speech = [], 0, False
        if len(frames) - self.end_frames < self.min_utterance_frames:
            return VadEvent("utterance", b"")  # too short to be speech: report as empty
        return VadEvent("utterance", b"".join(frames))
