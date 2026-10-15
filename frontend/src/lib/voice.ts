// Browser side of WS /api/v1/interviews/{id}/voice (see knowledge_transfer/api/v1/routes/voice.py).
//
// Sends 16 kHz mono PCM16 microphone frames. Receives JSON events and audio clips; each clip
// is a JSON {"type": "audio"} header followed by one binary frame. After the last clip of
// speech n has played, sends {"type": "playback_done", "id": n}. A "clear" event means the
// leaver spoke over the agent: queued and playing audio is dropped at once.

export type VoiceState = "connecting" | "speaking" | "listening" | "processing" | "ended" | "closed";

export type VoiceEvent =
  | { type: "state"; state: "speaking" | "listening" | "processing" | "ended" }
  | { type: "transcript"; role: "agent" | "user"; text: string; amend?: boolean; item_id?: string; reasons?: string[] }
  | { type: "saved"; item_id: string; answer_type: string; new_items: string[] }
  | { type: "clear" }
  | { type: "audio_end"; id: number }
  | { type: "audio"; kind: string; format: string }
  | { type: "error"; message: string }
  | { type: "ended"; reason: string };

export interface VoiceCallbacks {
  onEvent: (event: VoiceEvent) => void;
  onState: (state: VoiceState) => void;
  onError: (message: string) => void;
}

const SAMPLE_RATE = 16000;

// Runs on the audio thread: float samples in, PCM16 frames out.
const CAPTURE_WORKLET = `
class Capture extends AudioWorkletProcessor {
  process(inputs) {
    const ch = inputs[0][0];
    if (ch) {
      const out = new Int16Array(ch.length);
      for (let i = 0; i < ch.length; i++) {
        const s = Math.max(-1, Math.min(1, ch[i]));
        out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      this.port.postMessage(out.buffer, [out.buffer]);
    }
    return true;
  }
}
registerProcessor("capture", Capture);
`;

export function voiceSocketUrl(interviewId: string): string {
  const configured = process.env.NEXT_PUBLIC_VOICE_WS_URL;
  const base = configured
    ? configured.replace(/\/$/, "")
    : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.hostname}:8000`;
  return `${base}/api/v1/interviews/${encodeURIComponent(interviewId)}/voice`;
}

export class VoiceClient {
  private ctx: AudioContext | null = null;
  private mic: MediaStream | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private worklet: AudioWorkletNode | null = null;
  private ws: WebSocket | null = null;
  private stopped = false;

  // Playback. `epoch` invalidates clips that were still decoding when "clear" arrived.
  private epoch = 0;
  private chain: Promise<void> = Promise.resolve();
  private queue: AudioBuffer[] = [];
  private playing: AudioBufferSourceNode | null = null;
  private endId: number | null = null;

  constructor(
    private readonly interviewId: string,
    private readonly cb: VoiceCallbacks,
  ) {}

  /** Must be called from a user gesture (a click), or the browser keeps audio suspended. */
  async start(): Promise<void> {
    this.cb.onState("connecting");
    try {
      const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
      this.ctx = ctx;
      await ctx.resume();
      this.mic = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      // stop() may have run while the permission prompt was open; release what was acquired.
      if (this.stopped) return this.teardown();
      const url = URL.createObjectURL(new Blob([CAPTURE_WORKLET], { type: "text/javascript" }));
      try {
        await ctx.audioWorklet.addModule(url);
      } finally {
        URL.revokeObjectURL(url);
      }
      if (this.stopped) return this.teardown();
      this.connect();
    } catch (e) {
      if (this.stopped) return;
      this.cb.onError(describeStartError(e));
      this.stop();
    }
  }

  stop(): void {
    this.stopped = true;
    if (this.ws && this.ws.readyState <= WebSocket.OPEN) this.ws.close();
    this.teardown();
    this.cb.onState("closed");
  }

  private connect(): void {
    const ws = new WebSocket(voiceSocketUrl(this.interviewId));
    ws.binaryType = "arraybuffer";
    this.ws = ws;
    ws.onopen = () => {
      if (!this.ctx || !this.mic) return;
      try {
        // Firefox throws here when the microphone's sample rate differs from the context's.
        this.source = this.ctx.createMediaStreamSource(this.mic);
        this.worklet = new AudioWorkletNode(this.ctx, "capture");
      } catch (e) {
        this.cb.onError(describeStartError(e));
        this.stop();
        return;
      }
      this.worklet.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
        if (ws.readyState === WebSocket.OPEN) ws.send(e.data);
      };
      this.source.connect(this.worklet);
    };
    ws.onmessage = (ev: MessageEvent<ArrayBuffer | string>) => this.onMessage(ev.data);
    ws.onerror = () => {
      if (!this.stopped) this.cb.onError("The voice connection failed. Check that the API server is reachable.");
    };
    ws.onclose = () => {
      if (!this.stopped) this.stop();
    };
  }

  private onMessage(data: ArrayBuffer | string): void {
    if (data instanceof ArrayBuffer) {
      this.enqueue(data);
      return;
    }
    let event: VoiceEvent;
    try {
      event = JSON.parse(data) as VoiceEvent;
    } catch {
      return;
    }
    switch (event.type) {
      case "state":
        this.cb.onState(event.state);
        break;
      case "clear":
        this.clearAudio();
        break;
      case "audio_end":
        this.markEnd(event.id);
        break;
      case "ended":
        this.cb.onState("ended");
        break;
    }
    this.cb.onEvent(event);
  }

  // ---- playback ------------------------------------------------------------

  private enqueue(bytes: ArrayBuffer): void {
    const epoch = this.epoch;
    this.chain = this.chain.then(async () => {
      if (!this.ctx || this.ctx.state === "closed") return;
      try {
        const buffer = await this.ctx.decodeAudioData(bytes.slice(0));
        if (epoch === this.epoch) {
          this.queue.push(buffer);
          this.pump();
        }
      } catch {
        if (!this.stopped) this.cb.onError("Could not play a clip of the agent's speech.");
      }
    });
  }

  private markEnd(id: number): void {
    const epoch = this.epoch;
    this.chain = this.chain.then(() => {
      if (epoch === this.epoch) {
        this.endId = id;
        this.pump();
      }
    });
  }

  private pump(): void {
    if (this.playing || !this.ctx) return;
    const next = this.queue.shift();
    if (!next) {
      if (this.endId !== null && this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "playback_done", id: this.endId }));
      }
      this.endId = null;
      return;
    }
    const src = this.ctx.createBufferSource();
    src.buffer = next;
    src.connect(this.ctx.destination);
    src.onended = () => {
      if (this.playing === src) {
        this.playing = null;
        this.pump();
      }
    };
    this.playing = src;
    src.start();
  }

  private clearAudio(): void {
    this.epoch++;
    this.queue = [];
    this.endId = null;
    const p = this.playing;
    this.playing = null;
    if (p) {
      p.onended = null;
      try {
        p.stop();
      } catch {
        // Already stopped.
      }
    }
  }

  private teardown(): void {
    this.clearAudio();
    this.worklet?.port.close();
    this.worklet?.disconnect();
    this.source?.disconnect();
    this.mic?.getTracks().forEach((t) => t.stop());
    if (this.ctx && this.ctx.state !== "closed") void this.ctx.close();
    this.worklet = null;
    this.source = null;
    this.mic = null;
    this.ctx = null;
  }
}

function describeStartError(e: unknown): string {
  if (e instanceof DOMException) {
    if (e.name === "NotAllowedError") return "Microphone access was blocked. Allow it in the browser's site settings and try again.";
    if (e.name === "NotFoundError") return "No microphone was found.";
    if (e.name === "NotSupportedError") {
      return "This browser cannot record at 16 kHz. Use a current version of Chrome or Edge.";
    }
  }
  if (typeof window !== "undefined" && !window.isSecureContext) {
    return "The microphone only works on https or localhost.";
  }
  return `Could not start voice: ${e instanceof Error ? e.message : String(e)}`;
}
