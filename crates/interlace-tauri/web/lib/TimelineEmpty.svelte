<script lang="ts">
  import type { TimelineRow } from "./api";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import EmptyState from "$lib/EmptyState.svelte";

  let {
    tlLoading,
    tlAppending,
    selectedId,
    tlError,
    timeline,
    filteredTimeline,
    includeGroups,
    onRetry,
    onShowAll,
    onIncludeGroups,
    onImport,
  }: {
    tlLoading: boolean;
    tlAppending: boolean;
    selectedId: number | null;
    tlError: string;
    timeline: TimelineRow[];
    filteredTimeline: { index: number }[];
    includeGroups: boolean;
    onRetry: () => void;
    onShowAll: () => void;
    onIncludeGroups: () => void;
    onImport: () => void;
  } = $props();
</script>

{#if tlLoading}
  {#if !tlAppending}
    <div class="space-y-2 pt-2" aria-hidden="true">
      <Skeleton class="h-4 w-[92%]" />
      <Skeleton class="h-3 w-[68%]" />
      <Skeleton class="h-4 w-[84%]" />
      <Skeleton class="h-3 w-[56%]" />
      <Skeleton class="h-4 w-[76%]" />
    </div>
  {/if}
{:else if !selectedId}
  <div class="py-6">
    <EmptyState
      title="Select a person"
      body="Click a name on the left. Groups stay hidden until you tick include groups."
      actionLabel="People"
      onAction={() => document.getElementById("person-filter")?.focus()}
    />
  </div>
{:else if tlError}
  <div class="py-6">
    <div class="rounded-md border border-destructive/40 bg-muted/40 px-4 py-6 text-sm" data-partial>
      <p class="font-medium text-destructive">Error</p>
      <p class="mt-1 text-muted-foreground">{tlError}</p>
      <Button size="sm" class="mt-3" onclick={onRetry}>Retry</Button>
    </div>
  </div>
{:else if filteredTimeline.length === 0}
  <div class="py-6">
    <EmptyState
      title="No messages in this view"
      body={timeline.length === 0
        ? "This person may only appear in groups. Tick include groups, or import more sources."
        : "Nothing matches the current platform or kind filter. Try All, or another chip."}
      actionLabel={timeline.length > 0 ? "Show all" : includeGroups ? "Import" : "Include groups"}
      onAction={() => {
        if (timeline.length > 0) {
          onShowAll();
          return;
        }
        if (selectedId && !includeGroups) {
          onIncludeGroups();
          return;
        }
        onImport();
      }}
    />
  </div>
{/if}
