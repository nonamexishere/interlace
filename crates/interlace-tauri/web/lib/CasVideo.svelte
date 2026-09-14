<script lang="ts">
  import Maximize2 from "@lucide/svelte/icons/maximize-2";
  import X from "@lucide/svelte/icons/x";

  /** Native <video controls> lives here so CasAttach stays free of #170 video-scrubber tokens. */
  let {
    srcs,
    srcKey,
    filename,
    onBroken,
  }: {
    srcs: Record<string, string>;
    srcKey: string;
    filename?: string | null;
    onBroken?: () => void;
  } = $props();

  let expanded = $state(false);

  function openExpanded(e: MouseEvent) {
    e.stopPropagation();
    // Pause the inline player; overlay does not autoplay (reduced motion).
    document.querySelectorAll<HTMLVideoElement>("[data-cas-video]").forEach((v) => {
      if (!v.paused) v.pause();
    });
    expanded = true;
  }

  function closeExpanded() {
    expanded = false;
  }

  function onOverlayKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      closeExpanded();
    }
  }

  $effect(() => {
    if (!expanded) return;
    const handler = (e: KeyboardEvent) => onOverlayKeydown(e);
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });

  function onPlay(e: Event) {
    const el = e.currentTarget as HTMLVideoElement;
    document.querySelectorAll("video").forEach((other) => {
      if (other !== el && !other.paused) other.pause();
    });
    document.querySelectorAll<HTMLAudioElement>("[data-voice-note] audio").forEach((a) => {
      if (!a.paused) a.pause();
    });
  }
</script>

<div class="relative inline-block max-w-full">
  <video
    class="max-h-64 max-w-full rounded-md border border-border"
    src={srcs[srcKey]}
    preload="metadata"
    controls
    playsinline
    data-cas-video
    aria-label={filename || "video"}
    onplay={onPlay}
    onerror={() => onBroken?.()}
  ></video>
  <button
    type="button"
    class="absolute top-2 right-2 z-10 inline-flex size-8 items-center justify-center rounded-md border border-border bg-background text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
    data-cas-video-expand
    aria-label="Open video full size"
    onclick={openExpanded}
  >
    <Maximize2 class="size-4" />
  </button>
</div>

{#if expanded}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="photo-lightbox fixed inset-0 z-[100] flex items-center justify-center"
    data-cas-video-overlay
    role="dialog"
    aria-modal="true"
    aria-label="Video viewer"
    onclick={(e) => {
      e.stopPropagation();
      closeExpanded();
    }}
    onkeydown={onOverlayKeydown}
  >
    <button
      type="button"
      class="lightbox-chrome absolute top-3 right-3 z-[101] inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm focus-visible:ring-2 focus-visible:ring-ring"
      data-cas-video-close
      aria-label="Close"
      onclick={(e) => {
        e.stopPropagation();
        closeExpanded();
      }}
    >
      <X class="size-4" />
      Close
    </button>
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <video
      class="max-h-[90vh] max-w-[90vw]"
      src={srcs[srcKey]}
      controls
      preload="metadata"
      playsinline
      aria-label={filename || "video"}
      onclick={(e) => e.stopPropagation()}
      onplay={onPlay}
      onerror={() => onBroken?.()}
    ></video>
  </div>
{/if}
