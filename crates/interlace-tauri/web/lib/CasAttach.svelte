<script lang="ts">
  import Play from "@lucide/svelte/icons/play";
  import Pause from "@lucide/svelte/icons/pause";
  import X from "@lucide/svelte/icons/x";
  import { api } from "./api";
  import { t } from "./i18n";
  import { togglePlay } from "./CasVoice";
  import CasPdf from "./CasPdf.svelte";
  import CasVideo from "./CasVideo.svelte";

  export type Attachment = {
    id: number;
    cas_hash?: string | null;
    filename?: string | null;
    mime?: string | null;
    kind: string;
    omitted: boolean;
    missing: boolean;
  };

  let {
    items,
    showToast,
    flush = false,
  }: {
    items: Attachment[];
    showToast?: (message: string) => void;
    flush?: boolean;
  } = $props();

  function isImage(a: Attachment) {
    const m = (a.mime || "").toLowerCase();
    const n = (a.filename || "").toLowerCase();
    return (
      a.kind === "image" ||
      a.kind === "sticker" ||
      m.startsWith("image/") ||
      /\.(jpe?g|png|gif|webp|bmp)$/.test(n)
    );
  }

  function isAudio(a: Attachment) {
    const m = (a.mime || "").toLowerCase();
    const n = (a.filename || "").toLowerCase();
    return a.kind === "voice" || m.startsWith("audio/") || /\.(opus|ogg|mp3|m4a|aac|wav)$/.test(n);
  }

  function isVideo(a: Attachment) {
    const m = (a.mime || "").toLowerCase();
    const n = (a.filename || "").toLowerCase();
    return (
      a.kind === "video" ||
      m.startsWith("video/") ||
      /\.(mp4|mov|mkv|avi|webm)$/.test(n)
    );
  }

  function isPdf(a: Attachment) {
    const m = (a.mime || "").toLowerCase();
    const n = (a.filename || "").toLowerCase();
    return m === "application/pdf" || n.endsWith(".pdf");
  }

  let srcs = $state<Record<string, string>>({});
  let broken = $state<Record<string, boolean>>({});
  const requested = new Set<string>();

  function hashOf(a: Attachment): string | null {
    const h = a.cas_hash ?? (a as { casHash?: string | null }).casHash;
    return h || null;
  }

  function keyOf(a: Attachment): string {
    return hashOf(a) || a.filename || String(a.id);
  }

  $effect(() => {
    for (const a of items || []) {
      const hash = hashOf(a);
      const k = keyOf(a);
      if (!hash || requested.has(k)) continue;
      requested.add(k);
      api
        .casDataUrl(hash)
        .then((url) => {
          srcs = { ...srcs, [k]: url };
        })
        .catch(() => {
          broken = { ...broken, [k]: true };
        });
    }
  });

  // Loadable image attachments on this message (for lightbox prev/next).
  function imageItems(): Attachment[] {
    return (items || []).filter(
      (a) =>
        !a.omitted &&
        !a.missing &&
        hashOf(a) &&
        isImage(a) &&
        srcs[keyOf(a)] &&
        !broken[keyOf(a)],
    );
  }

  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  function openLightbox(a: Attachment) {
    const imgs = imageItems();
    const idx = imgs.findIndex((x) => keyOf(x) === keyOf(a));
    if (idx < 0) return;
    lightboxIndex = idx;
    lightboxOpen = true;
  }

  function closeLightbox() {
    lightboxOpen = false;
  }

  function showPrev() {
    const imgs = imageItems();
    if (imgs.length < 2) return;
    lightboxIndex = (lightboxIndex - 1 + imgs.length) % imgs.length;
  }

  function showNext() {
    const imgs = imageItems();
    if (imgs.length < 2) return;
    lightboxIndex = (lightboxIndex + 1) % imgs.length;
  }

  function onLightboxKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      closeLightbox();
      return;
    }
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      showPrev();
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      showNext();
    }
  }

  $effect(() => {
    if (!lightboxOpen) return;
    const handler = (e: KeyboardEvent) => onLightboxKeydown(e);
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });

  let revealMenu = $state<{ x: number; y: number; hash: string } | null>(null);

  function openRevealMenu(e: MouseEvent, hash: string) {
    e.preventDefault();
    e.stopPropagation();
    revealMenu = { x: e.clientX, y: e.clientY, hash };
  }

  function closeRevealMenu() {
    revealMenu = null;
  }

  async function revealInFinder() {
    if (!revealMenu) return;
    const hash = revealMenu.hash;
    revealMenu = null;
    try {
      await api.revealCas(hash);
    } catch {
      if (showToast) showToast("Could not reveal");
    }
  }

  function onRevealAway(e: MouseEvent) {
    if (!revealMenu) return;
    const el = e.target as HTMLElement | null;
    if (el?.closest("[data-reveal-menu]")) return;
    closeRevealMenu();
  }

  function onRevealKey(e: KeyboardEvent) {
    if (e.key === "Escape") closeRevealMenu();
  }

  $effect(() => {
    if (!revealMenu) return;
    window.addEventListener("keydown", onRevealKey);
    window.addEventListener("mousedown", onRevealAway);
    return () => {
      window.removeEventListener("keydown", onRevealKey);
      window.removeEventListener("mousedown", onRevealAway);
    };
  });

  function lightboxSrc(): string | null {
    const imgs = imageItems();
    const a = imgs[lightboxIndex];
    if (!a) return null;
    return srcs[keyOf(a)] || null;
  }

  function lightboxAlt(): string {
    const imgs = imageItems();
    const a = imgs[lightboxIndex];
    return a?.filename || "image";
  }

  let playing = $state<Record<string, boolean>>({});
  let currentTimes = $state<Record<string, number>>({});
  let durations = $state<Record<string, number>>({});

  function formatTime(sec: number): string {
    if (!Number.isFinite(sec) || sec < 0) return "0:00";
    const s = Math.floor(sec);
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}:${String(r).padStart(2, "0")}`;
  }

  function setDuration(key: string, d: number) {
    if (!Number.isFinite(d) || d <= 0) return;
    durations = { ...durations, [key]: d };
  }

  function voiceAudioFrom(el: HTMLElement | null): HTMLAudioElement | null {
    const wrap = el?.closest("[data-voice-note]");
    return (wrap?.querySelector("audio") as HTMLAudioElement | null) ?? null;
  }

  function onVoicePlay(e: MouseEvent, key: string) {
    e.stopPropagation();
    const el = voiceAudioFrom(e.currentTarget as HTMLElement);
    if (!el) return;
    togglePlay(el, () => {
      broken = { ...broken, [key]: true };
    });
  }

  function seekVoice(e: Event, key: string) {
    e.stopPropagation();
    const input = e.currentTarget as HTMLInputElement;
    const el = voiceAudioFrom(input);
    if (!el) return;
    const next = Number(input.value);
    if (!Number.isFinite(next) || next < 0) return;
    el.currentTime = next;
    currentTimes = { ...currentTimes, [key]: next };
  }
</script>

{#if items?.length}
  <ul class={flush ? "space-y-2" : "mt-2 space-y-2"}>
    {#each items as a}
      <li
        oncontextmenu={(e) => {
          const hash = hashOf(a);
          if (!hash || a.omitted || a.missing) return;
          openRevealMenu(e, hash);
        }}
      >
        {#if a.omitted}
          <p class="text-xs text-muted-foreground">Media omitted in this export</p>
        {:else if a.missing || !hashOf(a)}
          <p class="text-xs text-muted-foreground">
            Photo/file not stored ({a.filename || "attachment"}). Re-import the WhatsApp ZIP from the
            Import tab (old messages stay, missing files are added).
          </p>
        {:else if isImage(a) && !broken[keyOf(a)]}
          <button
            type="button"
            class="block cursor-pointer border-0 bg-transparent p-0 text-left focus-visible:ring-2 focus-visible:ring-ring"
            onclick={(e) => {
              e.stopPropagation();
              openLightbox(a);
            }}
            aria-label={`Open ${a.filename || "image"} full size`}
          >
            <span data-cas-image-slot class="cas-image-slot max-h-64">
              {#if srcs[keyOf(a)]}
                <img
                  src={srcs[keyOf(a)]}
                  alt={a.filename || "image"}
                  class="max-h-64 max-w-full object-contain"
                  onerror={() => {
                    broken = { ...broken, [keyOf(a)]: true };
                  }}
                />
              {/if}
            </span>
          </button>
        {:else if isVideo(a) && srcs[keyOf(a)] && !broken[keyOf(a)]}
          <CasVideo
            srcs={srcs}
            srcKey={keyOf(a)}
            filename={a.filename}
            onBroken={() => {
              broken = { ...broken, [keyOf(a)]: true };
            }}
          />
        {:else if isPdf(a) && srcs[keyOf(a)] && !broken[keyOf(a)]}
          <CasPdf
            srcs={srcs}
            srcKey={keyOf(a)}
            filename={a.filename}
            onBroken={() => {
              broken = { ...broken, [keyOf(a)]: true };
            }}
          />
        {:else if isAudio(a) && srcs[keyOf(a)] && !broken[keyOf(a)]}
          {@const key = keyOf(a)}
          {@const dur = durations[key] ?? 0}
          <div
            class="voice-note flex max-w-xs items-center gap-2 rounded-full border border-border bg-muted/40 px-2 py-1.5"
            data-voice-note
          >
            <audio
              class="hidden"
              src={srcs[key]}
              preload="metadata"
              ontimeupdate={(e) => {
                const t = (e.currentTarget as HTMLAudioElement).currentTime;
                currentTimes = { ...currentTimes, [key]: t };
              }}
              onloadedmetadata={(e) => {
                setDuration(key, (e.currentTarget as HTMLAudioElement).duration);
              }}
              ondurationchange={(e) => {
                // Opus/Ogg often reports duration only after this event.
                setDuration(key, (e.currentTarget as HTMLAudioElement).duration);
              }}
              onplay={() => {
                playing = { ...playing, [key]: true };
              }}
              onpause={() => {
                playing = { ...playing, [key]: false };
              }}
              onended={(e) => {
                playing = { ...playing, [key]: false };
                currentTimes = { ...currentTimes, [key]: 0 };
                (e.currentTarget as HTMLAudioElement).currentTime = 0;
              }}
              onerror={() => {
                broken = { ...broken, [key]: true };
              }}
            ></audio>
            <button
              type="button"
              class="inline-flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground hover:bg-primary/90 focus-visible:ring-2 focus-visible:ring-ring"
              aria-label={playing[key] ? "Pause voice note" : "Play voice note"}
              data-voice-play
              onclick={(e) => onVoicePlay(e, key)}
            >
              {#if playing[key]}
                <Pause class="size-4" />
              {:else}
                <Play class="size-4" />
              {/if}
            </button>
            <input
              type="range"
              class="voice-seek min-w-12 flex-1 focus-visible:ring-2 focus-visible:ring-ring"
              min="0"
              max={Number.isFinite(dur) && dur > 0 ? dur : 0}
              step="any"
              value={currentTimes[key] ?? 0}
              disabled={!(Number.isFinite(dur) && dur > 0)}
              aria-label="Seek voice note"
              aria-valuenow={currentTimes[key] ?? 0}
              data-voice-seek
              oninput={(e) => seekVoice(e, key)}
              onchange={(e) => seekVoice(e, key)}
              onclick={(e) => e.stopPropagation()}
              onpointerdown={(e) => e.stopPropagation()}
            />
            <span
              class="shrink-0 font-mono text-xs tabular-nums text-muted-foreground"
              data-voice-time
            >
              {formatTime(currentTimes[key] ?? 0)}{#if Number.isFinite(dur) && dur > 0}
                {" "}/ {formatTime(dur)}{/if}
            </span>
          </div>
        {:else if !broken[keyOf(a)] && !srcs[keyOf(a)]}
          <p class="text-xs text-muted-foreground">Loading {a.filename || "attachment"}…</p>
        {:else}
          <p class="text-xs text-muted-foreground">
            Stored locally: {a.filename || a.kind}
            {#if a.mime}
              ({a.mime})
            {/if}
          </p>
        {/if}
      </li>
    {/each}
  </ul>
{/if}

{#if lightboxOpen && lightboxSrc()}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="photo-lightbox fixed inset-0 z-[100] flex items-center justify-center"
    data-photo-lightbox
    role="dialog"
    aria-modal="true"
    aria-label="Photo viewer"
    onclick={(e) => {
      e.stopPropagation();
      closeLightbox();
    }}
    onkeydown={onLightboxKeydown}
  >
    <button
      type="button"
      class="lightbox-chrome absolute top-3 right-3 z-[101] inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm focus-visible:ring-2 focus-visible:ring-ring"
      data-lightbox-close
      aria-label="Close photo"
      onclick={(e) => {
        e.stopPropagation();
        closeLightbox();
      }}
    >
      <X class="size-4" />
      Close
    </button>
    {#if imageItems().length > 1}
      <button
        type="button"
        class="lightbox-chrome absolute left-3 z-[101] rounded-md px-3 py-2 focus-visible:ring-2 focus-visible:ring-ring"
        data-lightbox-prev
        aria-label="Previous image"
        onclick={(e) => {
          e.stopPropagation();
          showPrev();
        }}
      >
        ←
      </button>
      <button
        type="button"
        class="lightbox-chrome absolute right-3 z-[101] rounded-md px-3 py-2 focus-visible:ring-2 focus-visible:ring-ring"
        data-lightbox-next
        aria-label="Next image"
        onclick={(e) => {
          e.stopPropagation();
          showNext();
        }}
      >
        →
      </button>
    {/if}
    <!-- stopPropagation so clicking the image does not close -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <img
      src={lightboxSrc()}
      alt={lightboxAlt()}
      class="max-h-[90vh] max-w-[90vw] object-contain"
      onclick={(e) => e.stopPropagation()}
    />
  </div>
{/if}

{#if revealMenu}
  <div
    class="fixed z-[80] min-w-32 rounded-md border border-border bg-background py-1 shadow-md"
    style="left: {revealMenu.x}px; top: {revealMenu.y}px"
    data-reveal-menu
    data-context-menu
    role="menu"
  >
    <button
      type="button"
      class="block w-full px-3 py-1.5 text-left text-sm hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
      role="menuitem"
      onclick={revealInFinder}>{t("revealInFinder")}</button
    >
  </div>
{/if}
