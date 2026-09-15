<script lang="ts">
  import { Separator } from "$lib/components/ui/separator/index.js";
  import { t } from "$lib/i18n";
  import { kindLabel, platformLabel } from "./TimelineMail";

  let {
    availablePlatforms,
    availableKinds,
    platformFilter = $bindable("all"),
    kindFilter = $bindable("all"),
    attachKindFilter = $bindable("all"),
    fromMeFilter = $bindable("all"),
    onAttachKindChange,
  }: {
    availablePlatforms: string[];
    availableKinds: string[];
    platformFilter?: string;
    kindFilter?: string;
    attachKindFilter?: string;
    fromMeFilter?: string;
    onAttachKindChange?: () => void;
  } = $props();

  function pickAttachKind(kind: string) {
    if (attachKindFilter === kind) return;
    attachKindFilter = kind;
    onAttachKindChange?.();
  }
</script>

<div
  class="timeline-filters mb-4 space-y-2.5 rounded-lg border border-border bg-muted/40 px-3 py-2.5"
  data-timeline-filters
>
  {#if availablePlatforms.length > 0}
    <div
      data-platform-filter
      class="platform-filter flex flex-wrap items-center gap-x-2 gap-y-1.5"
      role="toolbar"
      aria-label="Filter by platform"
    >
      <span class="filter-section-label shrink-0 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground"
        >Platform</span
      >
      <div class="flex min-w-0 flex-wrap items-center gap-1.5">
        <button
          type="button"
          class="filter-chip rounded-full border px-2.5 py-0.5 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring {platformFilter ===
          'all'
            ? 'filter-chip-active border-border bg-background font-medium text-foreground shadow-sm'
            : 'border-transparent bg-transparent text-muted-foreground hover:bg-background/70 hover:text-foreground'}"
          onclick={() => (platformFilter = "all")}
        >
          All
        </button>
        {#each availablePlatforms as p}
          <button
            type="button"
            class="filter-chip rounded-full border px-2.5 py-0.5 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring {platformFilter ===
            p
              ? 'filter-chip-active border-border bg-background font-medium text-foreground shadow-sm'
              : 'border-transparent bg-transparent text-muted-foreground hover:bg-background/70 hover:text-foreground'}"
            onclick={() => (platformFilter = p)}
          >
            {platformLabel(p)}
          </button>
        {/each}
      </div>
    </div>
  {/if}
  {#if availablePlatforms.length > 0 && availableKinds.length > 0}
    <Separator />
  {/if}
  {#if availableKinds.length > 0}
    <div
      data-kind-filter
      class="kind-filter flex flex-wrap items-center gap-x-2 gap-y-1.5"
      role="toolbar"
      aria-label="Filter by kind"
    >
      <span class="filter-section-label shrink-0 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground"
        >Kind</span
      >
      <div class="flex min-w-0 flex-wrap items-center gap-1.5">
        <button
          type="button"
          class="filter-chip rounded-full border px-2.5 py-0.5 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring {kindFilter ===
          'all'
            ? 'filter-chip-active border-border bg-background font-medium text-foreground shadow-sm'
            : 'border-transparent bg-transparent text-muted-foreground hover:bg-background/70 hover:text-foreground'}"
          onclick={() => (kindFilter = "all")}
        >
          All
        </button>
        {#each availableKinds as k}
          <button
            type="button"
            class="filter-chip rounded-full border px-2.5 py-0.5 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring {kindFilter ===
            k
              ? 'filter-chip-active border-border bg-background font-medium text-foreground shadow-sm'
              : 'border-transparent bg-transparent text-muted-foreground hover:bg-background/70 hover:text-foreground'}"
            onclick={() => (kindFilter = k)}
          >
            {kindLabel(k)}
          </button>
        {/each}
      </div>
    </div>
  {/if}
  {#if availablePlatforms.length > 0 || availableKinds.length > 0}
    <Separator />
  {/if}
  <div
    class="attach-kind-filter flex flex-wrap items-center gap-x-2 gap-y-1.5"
    role="toolbar"
    aria-label={t("attachKind")}
  >
    <span class="filter-section-label shrink-0 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">{t("attachKind")}</span>
    <div data-attach-kind-filter class="flex min-w-0 flex-wrap items-center gap-1.5">
      {#each [{ id: "all", l: t("attachKindAll") }, { id: "photos", l: t("attachKindPhotos") }, { id: "voice", l: t("attachKindVoice") }, { id: "video", l: t("attachKindVideo") }, { id: "files", l: t("attachKindFiles") }] as chip}
        <button
          type="button"
          class="filter-chip rounded-full border px-2.5 py-0.5 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring {attachKindFilter ===
          chip.id
            ? 'filter-chip-active border-border bg-background font-medium text-foreground shadow-sm'
            : 'border-transparent bg-transparent text-muted-foreground hover:bg-background/70 hover:text-foreground'}"
          onclick={() => pickAttachKind(chip.id)}
        >
          {chip.l}
        </button>
      {/each}
    </div>
  </div>
  <Separator />
  <div
    class="from-me-filter flex flex-wrap items-center gap-x-2 gap-y-1.5"
    role="toolbar"
    aria-label={t("fromMe")}
  >
    <span class="filter-section-label shrink-0 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">{t("fromMe")}</span>
    <div data-from-me-filter class="flex min-w-0 flex-wrap items-center gap-1.5">
      {#each [{ id: "all", l: t("fromMeAll") }, { id: "them", l: t("fromMeThem") }, { id: "me", l: t("fromMeMe") }] as chip}
        <button
          type="button"
          class="filter-chip rounded-full border px-2.5 py-0.5 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring {fromMeFilter ===
          chip.id
            ? 'filter-chip-active border-border bg-background font-medium text-foreground shadow-sm'
            : 'border-transparent bg-transparent text-muted-foreground hover:bg-background/70 hover:text-foreground'}"
          onclick={() => (fromMeFilter = chip.id)}
        >
          {chip.l}
        </button>
      {/each}
    </div>
  </div>
</div>
