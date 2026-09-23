import { armVoiceSeek, publishVoice, voiceBroken } from "./voiceHost";

let offsetGen = 0;
let offsetHost: HTMLAudioElement | null = null;
let offsetListener: (() => void) | null = null;

function dropOffsetListener() {
  if (offsetHost && offsetListener) offsetHost.removeEventListener("loadedmetadata", offsetListener);
  offsetHost = null;
  offsetListener = null;
  offsetGen += 1;
}

function playErrorName(err: unknown): string {
  return err && typeof err === "object" && "name" in err ? String((err as { name: string }).name) : "";
}

/** Play/pause one local voice note. Pauses every other [data-voice-note] audio. */
export function togglePlay(el: HTMLAudioElement, onBroken?: () => void): void {
  const host = document.querySelector<HTMLAudioElement>("[data-voice-host] audio");
  const inTimeline = !!el.closest("#person-timeline");
  if (host && inTimeline) {
    dropOffsetListener();
    const key = el.dataset.voiceKey || "";
    const messageId = Number(el.dataset.voiceMsg || "0");
    const same =
      host.dataset.voiceKey === key &&
      host.dataset.voiceMsg === String(messageId) &&
      !!host.getAttribute("src");
    document.querySelectorAll<HTMLAudioElement>("[data-voice-note] audio").forEach((other) => {
      if (other !== host && !other.paused) other.pause();
    });
    if (same && !host.paused) {
      host.pause();
      el.pause();
      publishVoice({ playing: false });
      return;
    }
    const at = el.currentTime;
    if (!same) {
      host.src = el.src;
      host.dataset.voiceMsg = String(messageId);
      host.dataset.voiceKey = key;
    }
    el.pause();
    publishVoice({ messageId, key, playing: false });
    const gen = offsetGen;
    void host.play().then(() => {
      if (host.dataset.voiceKey !== key || host.dataset.voiceMsg !== String(messageId)) return;
      publishVoice({ messageId, key, playing: true });
    }).catch((err: unknown) => {
      const name = playErrorName(err);
      if (host.dataset.voiceKey === key && host.dataset.voiceMsg === String(messageId)) {
        publishVoice({ playing: false });
      }
      if (name === "AbortError" || name === "NotAllowedError") return;
      voiceBroken[key] = true;
      onBroken?.();
    });
    if (Number.isFinite(at) && at > 0) {
      const wantMsg = String(messageId);
      const applyAt = () => {
        if (gen !== offsetGen) return;
        if (host.dataset.voiceKey !== key || host.dataset.voiceMsg !== wantMsg) return;
        armVoiceSeek();
        host.currentTime = at;
      };
      if (host.readyState >= 1) applyAt();
      else {
        offsetListener = applyAt;
        offsetHost = host;
        host.addEventListener("loadedmetadata", applyAt, { once: true });
      }
    }
    return;
  }
  if (el.paused) {
    document.querySelectorAll<HTMLAudioElement>("[data-voice-note] audio").forEach((other) => {
      if (other !== el && !other.paused) other.pause();
    });
    void el.play().catch((err: unknown) => {
      const name = playErrorName(err);
      if (name === "AbortError" || name === "NotAllowedError") return;
      onBroken?.();
    });
  } else {
    el.pause();
  }
}
