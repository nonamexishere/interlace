<script lang="ts">
  import { api } from "./api";
  import { t } from "./i18n";

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
    onError,
  }: {
    items: Attachment[];
    onError?: (e: unknown) => void;
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
    } catch (e) {
      onError?.(e);
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

  function togglePlay(e: MouseEvent, key: string) {
    e.stopPropagation();
    const wrap = (e.currentTarget as HTMLElement).closest("[data-voice-note]");
    const el = wrap?.querySelector("audio") as HTMLAudioElement | null;
    if (!el) return;
    if (el.paused) {
      // One voice note at a time (document-wide so multiple CasAttach instances share).
      document.querySelectorAll<HTMLAudioElement>("[data-voice-note] audio").forEach((other) => {
        if (other !== el && !other.paused) other.pause();
      });
      void el.play().catch((err: unknown) => {
        // pause() / switching notes aborts a pending play(); not a bad file.
        const name = err && typeof err === "object" && "name" in err ? String((err as { name: string }).name) : "";
        if (name === "AbortError" || name === "NotAllowedError") return;
        broken = { ...broken, [key]: true };
      });
    } else {
      el.pause();
    }
  }
</script>

{#if items?.length}
  <ul class="mt-2 space-y-2">
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
        {:else if isImage(a) && srcs[keyOf(a)] && !broken[keyOf(a)]}
          <button
            type="button"
            class="block cursor-pointer border-0 bg-transparent p-0 text-left"
            onclick={(e) => {
              e.stopPropagation();
              openLightbox(a);
            }}
            aria-label={`Open ${a.filename || "image"} full size`}
          >
            <img
              src={srcs[keyOf(a)]}
              alt={a.filename || "image"}
              class="max-h-64 max-w-full rounded-md border border-border"
              onerror={() => {
                broken = { ...broken, [keyOf(a)]: true };
              }}
            />
          </button>
        {:else if isAudio(a) && srcs[keyOf(a)] && !broken[keyOf(a)]}
          {@const key = keyOf(a)}
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
              class="inline-flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground hover:bg-primary/90"
              aria-label={playing[key] ? "Pause voice note" : "Play voice note"}
              data-voice-play
              onclick={(e) => togglePlay(e, key)}
            >
              {#if playing[key]}
                <span class="text-[10px] leading-none" aria-hidden="true">❚❚</span>
              {:else}
                <span class="pl-0.5 text-xs leading-none" aria-hidden="true">▶</span>
              {/if}
            </button>
            <span
              class="min-w-0 flex-1 font-mono text-xs tabular-nums text-muted-foreground"
              data-voice-time
            >
              {formatTime(currentTimes[key] ?? 0)}{#if Number.isFinite(durations[key]) && (durations[key] ?? 0) > 0}
                {" "}/ {formatTime(durations[key] ?? 0)}{/if}
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
    class="photo-lightbox fixed inset-0 z-[100] flex items-center justify-center bg-black/80"
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
      class="absolute top-3 right-3 z-[101] rounded-md bg-black/50 px-3 py-1.5 text-sm text-white hover:bg-black/70"
      data-lightbox-close
      aria-label="Close photo"
      onclick={(e) => {
        e.stopPropagation();
        closeLightbox();
      }}
    >
      Close
    </button>
    {#if imageItems().length > 1}
      <button
        type="button"
        class="absolute left-3 z-[101] rounded-md bg-black/50 px-3 py-2 text-white hover:bg-black/70"
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
        class="absolute right-3 z-[101] rounded-md bg-black/50 px-3 py-2 text-white hover:bg-black/70"
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
      class="block w-full px-3 py-1.5 text-left text-sm hover:bg-muted"
      role="menuitem"
      onclick={revealInFinder}>{t("revealInFinder")}</button
    >
  </div>
{/if}
