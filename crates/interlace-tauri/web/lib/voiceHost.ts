import { api, type Attachment } from "./api";

/** Marker the People-timeline host audio wears. Search preview has no host. */
export const VOICE_HOST_ATTR = "data-voice-host";

export type VoiceSnap = {
  messageId: number;
  key: string;
  playing: boolean;
  time: number;
  duration: number;
};

type VoiceRow = { row: { message_id: number; attachments?: Attachment[] | null } };
type VoiceStep = { message_id: number; key: string; casDataUrl: string };

export const voiceUrls: Record<string, string> = {};
export const voiceBroken: Record<string, boolean> = {};

let snap: VoiceSnap = { messageId: 0, key: "", playing: false, time: 0, duration: 0 };
let seekHold = 0;
const listeners = new Set<() => void>();
const warmed = new Set<string>();

export function readVoice(): VoiceSnap {
  return snap;
}

export function subscribeVoice(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function publishVoice(partial: Partial<VoiceSnap>) {
  snap = { ...snap, ...partial };
  for (const fn of listeners) fn();
}

export function keyOf(a: Attachment): string {
  return a.cas_hash || a.filename || String(a.id);
}

export function isAudio(a: Attachment): boolean {
  const m = (a.mime || "").toLowerCase();
  const n = (a.filename || "").toLowerCase();
  return a.kind === "voice" || m.startsWith("audio/") || /\.(opus|ogg|mp3|m4a|aac|wav)$/.test(n);
}

export function armVoiceSeek() {
  seekHold = performance.now();
}

export function consumeSeekEnded(): boolean {
  const started = seekHold;
  seekHold = 0;
  if (!started) return false;
  return performance.now() - started < 400;
}

export function clearVoiceHost(host: HTMLAudioElement | null | undefined) {
  if (!host) return;
  host.pause();
  host.removeAttribute("src");
  host.src = "";
  delete host.dataset.voiceMsg;
  delete host.dataset.voiceKey;
  publishVoice({ playing: false, messageId: 0, key: "", time: 0, duration: 0 });
}

export function startVoiceHost(
  host: HTMLAudioElement,
  message_id: number,
  key: string,
  casDataUrl: string,
) {
  if (!casDataUrl) return;
  host.src = casDataUrl;
  host.dataset.voiceMsg = String(message_id);
  host.dataset.voiceKey = key;
  document.querySelectorAll<HTMLAudioElement>("#person-timeline [data-voice-note] audio").forEach((row) => {
    if (!row.paused) row.pause();
  });
  publishVoice({ messageId: message_id, key, playing: true, time: 0 });
  void host.play().catch(() => {
    voiceBroken[key] = true;
    publishVoice({ playing: false });
  });
}

/** Next playable note below `currentKey` on this message. No wrap, no fetch. */
export function nextPlayableVoice(
  filteredTimeline: VoiceRow[],
  messageId: number,
  currentKey: string,
): VoiceStep | null {
  let seen = false;
  for (const item of filteredTimeline) {
    const message_id = item.row.message_id;
    const used = new Set<string>();
    for (const a of item.row.attachments || []) {
      const key = keyOf(a);
      if (used.has(key)) continue;
      used.add(key);
      if (!seen) {
        if (message_id === messageId && key === currentKey) seen = true;
        continue;
      }
      if (a.omitted || a.missing) continue;
      if (!isAudio(a)) continue;
      const broken = voiceBroken[key] === true;
      if (broken) continue;
      const casDataUrl = voiceUrls[key];
      if (!casDataUrl) continue;
      return { message_id, key, casDataUrl };
    }
  }
  return null;
}

export function warmVoiceUrls(filteredTimeline: VoiceRow[]) {
  for (const item of filteredTimeline) {
    for (const a of item.row.attachments || []) {
      if (a.omitted || a.missing || !a.cas_hash) continue;
      if (!isAudio(a)) continue;
      const key = keyOf(a);
      if (warmed.has(key) || voiceUrls[key] || voiceBroken[key]) continue;
      warmed.add(key);
      const hash = a.cas_hash;
      void api
        .casDataUrl(hash)
        .then((url) => {
          voiceUrls[key] = url;
        })
        .catch(() => {
          voiceBroken[key] = true;
        });
    }
  }
}
