<script lang="ts">
  import type { SearchHit } from "./api";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import EmptyState from "./EmptyState.svelte";
  import CasAttach from "./CasAttach.svelte";
  import { splitSnippet } from "./snippetHighlight";
  import { humanTime } from "./formatTime";

  let {
    hits,
    hitIndex = $bindable(0),
    expanded,
    body,
    searching,
    searched,
    searchError,
    empty,
    onRetry,
    onActivate,
    onToast,
  }: {
    hits: SearchHit[];
    hitIndex?: number;
    expanded: number | null;
    body: string;
    searching: boolean;
    searched: boolean;
    searchError: string;
    empty: boolean;
    onRetry: () => void;
    onActivate: (h: SearchHit, i: number) => void;
    onToast?: (message: string) => void;
  } = $props();
</script>

{#if searching && !hits.length}
  <div class="space-y-2" aria-hidden="true">
    <Skeleton class="h-4 w-[90%]" />
    <Skeleton class="h-3 w-[64%]" />
    <Skeleton class="h-4 w-[82%]" />
    <Skeleton class="h-3 w-[50%]" />
    <Skeleton class="h-4 w-[74%]" />
  </div>
{:else if !searched}
  <EmptyState
    title="Type a query"
    body="Same full-text search as the CLI. Group chats stay hidden until you tick include groups."
    actionLabel="Focus search"
    onAction={() => document.getElementById("q")?.focus()}
  />
{:else if searchError}
  <div
    class="rounded-md border border-destructive/40 bg-muted/40 px-4 py-6 text-sm"
    data-partial
  >
    <p class="font-medium text-destructive">Error</p>
    <p class="mt-1 text-muted-foreground">{searchError}</p>
    <Button size="sm" class="mt-3" onclick={onRetry}>Retry</Button>
  </div>
{:else if empty}
  <EmptyState
    title="No hits"
    body="Try another token, widen the date range, or enable include groups if the match is only in a group."
    actionLabel="Focus search"
    onAction={() => document.getElementById("q")?.focus()}
  />
{/if}

<ol class="divide-y divide-border" data-search-hits>
  {#each hits as h, i}
    <li
      class="px-1 py-2"
      class:bg-accent={i === hitIndex}
      data-search-hit={i}
    >
      <button
        type="button"
        class="w-full rounded-md text-left hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring {i === hitIndex
          ? 'ring-2 ring-ring'
          : ''}"
        onclick={() => onActivate(h, i)}
      >
        <div class="text-xs text-muted-foreground">
          {[humanTime(h.sent_at, h.platform), h.person_name || h.conversation_title || ""]}
            .filter(Boolean)
            .join(" · ")}
        </div>
        <p class="mt-1 whitespace-pre-wrap text-sm leading-normal">
          {#each splitSnippet(h.snippet || h.subject || "") as seg}
            {#if seg.kind === "mark"}
              <mark class="search-mark">{seg.text}</mark>
            {:else}
              {seg.text}
            {/if}
          {/each}
        </p>
      </button>
      <CasAttach items={h.attachments || []} showToast={onToast} />
      {#if expanded === h.message_id}
        <p class="bg-muted px-2 py-2 text-sm leading-normal whitespace-pre-wrap">{body}</p>
      {/if}
    </li>
  {/each}
</ol>
{#if hits.length > 0}
  <p class="mt-2 text-xs text-muted-foreground">
    <kbd class="rounded border border-border px-1">j</kbd>/<kbd
      class="rounded border border-border px-1">k</kbd
    >
    or arrows move hits;
    <kbd class="rounded border border-border px-1">Enter</kbd> opens on
    People when linked, else expands.
  </p>
{/if}
