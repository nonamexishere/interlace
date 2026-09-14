<script lang="ts">
  import X from "@lucide/svelte/icons/x";
  import Video from "@lucide/svelte/icons/video";
  import { api, type PersonMediaRow } from "./api";
  import CasVideo from "./CasVideo.svelte";
  import { writeIncludeGroupsPref } from "./PeoplePrefs";
  import EmptyState from "$lib/EmptyState.svelte";
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import { t } from "$lib/i18n";

  let {
    open = $bindable(false),
    selectedId,
    includeGroups = $bindable(false),
    onIncludeGroups,
    onImport,
    openPersonAtMessage,
  }: {
    open?: boolean;
    selectedId: number | null;
    includeGroups?: boolean;
    onIncludeGroups: () => void;
    onImport: () => void;
    openPersonAtMessage: (
      personId: number,
      messageId: number,
      sentAt?: string | null,
    ) => void | Promise<void>;
  } = $props();

  const VIRTUALIZE_AFTER = 48;
  const COLS = 4;
  const OVERSCAN_ROWS = 2;
  /** Fallback pitch until the first row is measured (thumb + caption + jump + gap). */
  const ROW_FALLBACK = 232;

  let galleryGen = 0;
  let overlayGen = 0;
  let mediaRows = $state<PersonMediaRow[]>([]);
  let srcs = $state<Record<string, string>>({});
  let mediaLoading = $state(false);
  let scrollTop = $state(0);
  let viewportH = $state(400);
  let rowH = $state(ROW_FALLBACK);
  let galleryEl = $state<HTMLDivElement | null>(null);
  let lightboxSrc = $state<string | null>(null);
  let lightboxAlt = $state("");
  let videoSrc = $state<string | null>(null);
  let videoName = $state("");
  const requested = new Set<string>();
  const overlayOpen = $derived(lightboxSrc != null || videoSrc != null);

  function isVideoRow(row: PersonMediaRow): boolean {
    const mime = (row.mime || "").toLowerCase();
    return row.kind === "video" || (row.kind === "inline" && mime.startsWith("video/"));
  }

  $effect(() => {
    const id = selectedId;
    const groups = includeGroups;
    const shown = open;
    mediaRows = [];
    srcs = {};
    requested.clear();
    lightboxSrc = null;
    videoSrc = null;
    scrollTop = 0;
    galleryEl && (galleryEl.scrollTop = 0);
    const gen = ++galleryGen;
    if (!shown || id == null) {
      mediaLoading = false;
      return;
    }
    mediaLoading = true;
    api
      .personMedia({ id, includeGroups: groups, limit: 200 })
      .then((rows) => {
        if (gen !== galleryGen) return;
        mediaRows = rows;
      })
      .catch(() => {
        if (gen !== galleryGen) return;
        mediaRows = [];
      })
      .finally(() => {
        if (gen !== galleryGen) return;
        mediaLoading = false;
      });
  });

  function measureRowH() {
    if (!galleryEl) return;
    const items = galleryEl.querySelectorAll("li");
    if (items.length === 0) return;
    const first = items[0] as HTMLElement;
    const top = first.offsetTop;
    let pitch = 0;
    for (let i = 1; i < items.length; i++) {
      const y = (items[i] as HTMLElement).offsetTop;
      if (y > top + 1) {
        pitch = y - top;
        break;
      }
    }
    if (pitch <= 0) pitch = first.getBoundingClientRect().height + 8;
    if (pitch > 40 && Math.abs(pitch - rowH) > 0.5) rowH = pitch;
  }

  const startIndex = $derived.by(() => {
    const n = mediaRows.length;
    if (n <= 48) return 0;
    const firstRow = Math.floor(Math.max(0, scrollTop) / rowH);
    return Math.max(0, (firstRow - OVERSCAN_ROWS) * COLS);
  });

  const endIndex = $derived.by(() => {
    const n = mediaRows.length;
    if (n <= 48) return n;
    const firstRow = Math.floor(Math.max(0, scrollTop) / rowH);
    const visRows = Math.ceil(Math.max(viewportH, 200) / rowH);
    return Math.min(n, (firstRow + visRows + OVERSCAN_ROWS) * COLS);
  });

  const galleryWindow = $derived(mediaRows.slice(startIndex, endIndex));
  const padTop = $derived(Math.floor(startIndex / COLS) * rowH);
  const padBottom = $derived(
    Math.max(0, Math.ceil((mediaRows.length - endIndex) / COLS) * rowH),
  );

  $effect(() => {
    const el = galleryEl;
    if (!el) return;
    el.scrollTop = 0;
    viewportH = el.clientHeight || 400;
    measureRowH();
    const ro = new ResizeObserver(() => {
      viewportH = el.clientHeight || 400;
      measureRowH();
    });
    ro.observe(el);
    return () => ro.disconnect();
  });

  $effect(() => {
    galleryWindow;
    mediaLoading;
    measureRowH();
  });

  $effect(() => {
    const gen = galleryGen;
    for (const row of galleryWindow) {
      if (isVideoRow(row)) continue;
      const hash = row.cas_hash;
      if (!hash || requested.has(hash)) continue;
      requested.add(hash);
      api
        .casDataUrl(hash)
        .then((url) => {
          if (gen !== galleryGen) return;
          srcs = { ...srcs, [hash]: url };
        })
        .catch(() => {
          if (gen !== galleryGen) return;
        });
    }
  });

  function closeOverlays() {
    lightboxSrc = null;
    videoSrc = null;
  }

  async function openPhoto(row: PersonMediaRow) {
    const gen = galleryGen;
    const click = ++overlayGen;
    closeOverlays();
    const hash = row.cas_hash;
    let url = srcs[hash];
    if (!url) {
      try {
        url = await api.casDataUrl(hash);
        srcs = { ...srcs, [hash]: url };
      } catch {
        return;
      }
    }
    if (gen !== galleryGen || click !== overlayGen || !open) return;
    lightboxAlt = row.filename || "";
    closeOverlays();
    lightboxSrc = url;
  }

  async function openVideo(row: PersonMediaRow) {
    const gen = galleryGen;
    const click = ++overlayGen;
    closeOverlays();
    const hash = row.cas_hash;
    try {
      const url = srcs[hash] || (await api.casDataUrl(hash));
      srcs = { ...srcs, [hash]: url };
      if (gen !== galleryGen || click !== overlayGen || !open) return;
      videoName = row.filename || "";
      closeOverlays();
      videoSrc = url;
    } catch {
      return;
    }
  }

  function onCellClick(row: PersonMediaRow) {
    if (isVideoRow(row)) {
      void openVideo(row);
      return;
    }
    void openPhoto(row);
  }

  function showInTimeline(row: PersonMediaRow) {
    closeOverlays();
    open = false;
    if (selectedId == null) return;
    void openPersonAtMessage(selectedId, row.message_id, row.sent_at);
  }

  function emptyAction() {
    if (!includeGroups) {
      includeGroups = true;
      writeIncludeGroupsPref(true);
      onIncludeGroups();
      return;
    }
    open = false;
    onImport();
  }

  function onOverlayKey(e: KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      closeOverlays();
    }
  }

  $effect(() => {
    if (!lightboxSrc) return;
    const handler = (e: KeyboardEvent) => onOverlayKey(e);
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });
</script>

<Dialog.Root bind:open>
  <Dialog.Content
    class="max-w-3xl"
    interactOutsideBehavior={overlayOpen ? "ignore" : "close"}
    escapeKeydownBehavior={overlayOpen ? "ignore" : "close"}
    onInteractOutside={(e) => {
      if (overlayOpen) e.preventDefault();
    }}
    onEscapeKeydown={(e) => {
      if (!overlayOpen) return;
      e.preventDefault();
      closeOverlays();
    }}
  >
    <Dialog.Header>
      <Dialog.Title>{t("media")}</Dialog.Title>
    </Dialog.Header>
    <div
      bind:this={galleryEl}
      data-person-gallery
      class="max-h-[60vh] overflow-y-auto [overflow-anchor:none]"
      onscroll={(e) => {
        const el = e.currentTarget;
        scrollTop = el.scrollTop;
        viewportH = el.clientHeight;
      }}
    >
      {#if !mediaLoading && mediaRows.length === 0}
        <EmptyState
          title={t("noStoredMedia")}
          body={t("noStoredMediaBody")}
          actionLabel={includeGroups ? t("import") : t("includeGroups")}
          onAction={emptyAction}
        />
      {:else}
        <div class="spacer" style="height: {padTop}px"></div>
        <ul class="grid grid-cols-4 gap-2">
          {#each galleryWindow as row (row.attachment_id)}
            <li class="flex min-w-0 flex-col">
              <button
                type="button"
                class="flex aspect-square w-full shrink-0 items-center justify-center overflow-hidden rounded-md border border-border bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring"
                onclick={() => onCellClick(row)}
              >
                {#if isVideoRow(row)}
                  <Video class="size-8 text-muted-foreground" />
                {:else if srcs[row.cas_hash]}
                  <img
                    src={srcs[row.cas_hash]}
                    alt=""
                    class="size-full object-cover"
                  />
                {/if}
              </button>
              <p class="mt-1 h-4 truncate text-xs text-muted-foreground">
                {row.filename || ""}
              </p>
              <Button
                variant="ghost"
                size="sm"
                class="mt-0.5 h-7 px-1 text-xs"
                data-person-gallery-jump
                onclick={() => showInTimeline(row)}
              >
                {t("showInTimeline")}
              </Button>
            </li>
          {/each}
        </ul>
        <div class="spacer" style="height: {padBottom}px"></div>
      {/if}
    </div>
  </Dialog.Content>
  {#if open && lightboxSrc}
    <Dialog.Portal>
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="photo-lightbox pointer-events-auto fixed inset-0 z-[100] flex items-center justify-center"
        style="pointer-events: auto"
        data-photo-lightbox
        role="dialog"
        aria-modal="true"
        aria-label={t("media")}
        onclick={(e) => {
          e.stopPropagation();
          closeOverlays();
        }}
        onkeydown={onOverlayKey}
      >
        <button
          type="button"
          class="lightbox-chrome pointer-events-auto absolute top-3 right-3 z-[101] inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm focus-visible:ring-2 focus-visible:ring-ring"
          data-lightbox-close
          aria-label={t("media")}
          onclick={(e) => {
            e.stopPropagation();
            closeOverlays();
          }}
        >
          <X class="size-4" />
        </button>
        <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
        <img
          src={lightboxSrc}
          alt={lightboxAlt}
          class="max-h-[90vh] max-w-[90vw] object-contain"
          onclick={(e) => e.stopPropagation()}
        />
      </div>
    </Dialog.Portal>
  {/if}
  {#if open && videoSrc}
    <Dialog.Portal>
      <CasVideo
        srcs={{ gallery: videoSrc }}
        srcKey="gallery"
        filename={videoName}
        overlayOnly
        onClose={closeOverlays}
      />
    </Dialog.Portal>
  {/if}
</Dialog.Root>
