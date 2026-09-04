/** Play/pause one local voice note. Pauses every other [data-voice-note] audio. */
export function togglePlay(el: HTMLAudioElement, onBroken?: () => void): void {
  if (el.paused) {
    document.querySelectorAll<HTMLAudioElement>("[data-voice-note] audio").forEach((other) => {
      if (other !== el && !other.paused) other.pause();
    });
    void el.play().catch((err: unknown) => {
      const name = err && typeof err === "object" && "name" in err ? String((err as { name: string }).name) : "";
      if (name === "AbortError" || name === "NotAllowedError") return;
      onBroken?.();
    });
  } else {
    el.pause();
  }
}
