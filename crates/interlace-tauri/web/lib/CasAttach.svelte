<script lang="ts">
  import { api } from "./api";

  export type Attachment = {
    id: number;
    cas_hash?: string | null;
    filename?: string | null;
    mime?: string | null;
    kind: string;
    omitted: boolean;
    missing: boolean;
  };

  let { items }: { items: Attachment[] } = $props();

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
</script>

{#if items?.length}
  <ul class="mt-2 space-y-2">
    {#each items as a}
      <li>
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
          <audio
            class="w-full"
            controls
            src={srcs[keyOf(a)]}
            onerror={() => {
              broken = { ...broken, [keyOf(a)]: true };
            }}
          ></audio>
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
