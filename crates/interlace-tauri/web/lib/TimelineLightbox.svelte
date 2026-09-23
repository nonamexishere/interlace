<script lang="ts">
  import X from "@lucide/svelte/icons/x";

  let {
    src,
    alt,
    nextAtEnd,
    prevExhausted,
    onClose,
    onPrev,
    onNext,
    onBroken,
  }: {
    src: string;
    alt: string;
    nextAtEnd: boolean;
    prevExhausted: boolean;
    onClose: () => void;
    onPrev: () => void;
    onNext: () => void;
    onBroken: () => void;
  } = $props();

  function backdropClick(e: MouseEvent) {
    e.stopPropagation();
    onClose();
  }

  function closeClick(e: MouseEvent) {
    e.stopPropagation();
    onClose();
  }

  function prevClick(e: MouseEvent) {
    e.stopPropagation();
    if (!prevExhausted) onPrev();
  }

  function nextClick(e: MouseEvent) {
    e.stopPropagation();
    if (!nextAtEnd) onNext();
  }

  function imageClick(e: MouseEvent) {
    e.stopPropagation();
  }

  $effect(() => {
    const close = onClose;
    const prev = onPrev;
    const next = onNext;
    const atEnd = nextAtEnd;
    const exhausted = prevExhausted;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        close();
        return;
      }
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        e.stopPropagation();
        if (!exhausted) prev();
        return;
      }
      if (e.key === "ArrowRight") {
        e.preventDefault();
        e.stopPropagation();
        if (!atEnd) next();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="photo-lightbox fixed inset-0 z-[100] flex items-center justify-center"
  data-thread-lightbox
  data-photo-lightbox
  role="dialog"
  aria-modal="true"
  aria-label="Photo viewer"
  onclick={backdropClick}
>
  <button
    type="button"
    class="lightbox-chrome absolute top-3 right-3 z-[101] inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm focus-visible:ring-2 focus-visible:ring-ring"
    data-lightbox-close
    aria-label="Close photo"
    onclick={closeClick}
  >
    <X class="size-4" />
    Close
  </button>
  <button
    type="button"
    class="lightbox-chrome absolute left-3 z-[101] rounded-md px-3 py-2 focus-visible:ring-2 focus-visible:ring-ring"
    data-lightbox-prev
    aria-label="Previous image"
    disabled={prevExhausted}
    onclick={prevClick}
  >
    ←
  </button>
  <button
    type="button"
    class="lightbox-chrome absolute right-3 z-[101] rounded-md px-3 py-2 focus-visible:ring-2 focus-visible:ring-ring"
    data-lightbox-next
    aria-label="Next image"
    disabled={nextAtEnd}
    onclick={nextClick}
  >
    →
  </button>
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <img
    {src}
    {alt}
    class="max-h-[90vh] max-w-[90vw] object-contain"
    onclick={imageClick}
    onerror={onBroken}
  />
</div>
