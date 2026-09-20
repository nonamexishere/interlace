<script lang="ts">
  import type { SearchHit } from "./api";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import EmptyState from "./EmptyState.svelte";
  import CasAttach from "./CasAttach.svelte";
  import { splitSnippet } from "./snippetHighlight";
  import { humanTime } from "./formatTime";
  import { displayBody, isMailRow, splitQuotedBody } from "./TimelineMail";
  import { t } from "./i18n";

  let {
    hits,
    hitIndex = $bindable(0),
    previewBody,
    previewMessageId,
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
    previewBody: string;
    previewMessageId: number | null;
    searching: boolean;
    searched: boolean;
    searchError: string;
    empty: boolean;
    onRetry: () => void;
    onActivate: (h: SearchHit, i: number) => void;
    onToast?: (message: string) => void;
  } = $props();

  let quotedOpen = $state<Record<number, boolean>>({});

  const previewHit = $derived(
    previewMessageId == null
      ? null
      : (hits.find((h) => h.message_id === previewMessageId) ?? null),
  );
</script>

<div class="flex min-h-0 flex-1 flex-row">
  <ScrollArea class="min-h-0 min-w-0 flex-1">
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
        </li>
      {/each}
    </ol>
    {#if hits.length > 0}
      <p class="mt-2 text-xs text-muted-foreground">
        <kbd class="rounded border border-border px-1">j</kbd>/<kbd
          class="rounded border border-border px-1">k</kbd
        >
        or arrows select a hit;
        <kbd class="rounded border border-border px-1">Enter</kbd> opens on
        People when linked.
      </p>
    {/if}
  </ScrollArea>
  <div
    class="flex min-h-0 w-96 shrink-0 flex-col overflow-y-auto border-l border-border p-4"
    data-search-preview
  >
    {#if previewHit}
      <div class="text-xs text-muted-foreground">
        {humanTime(previewHit.sent_at, previewHit.platform)}
      </div>
      {#if (previewHit.subject ?? "").trim()}
        <p class="mt-1 text-sm font-medium">{previewHit.subject}</p>
      {/if}
      {#if isMailRow(previewHit)}
        {@const parts = splitQuotedBody(previewBody || "")}
        {#if parts.main || !parts.quoted}
          <p class="mt-2 whitespace-pre-wrap break-words text-sm leading-normal">
            {displayBody(parts.main)}
          </p>
        {/if}
        {#if parts.quoted}
          {#if quotedOpen[previewHit.message_id]}
            <p class="mt-1 whitespace-pre-wrap break-words text-sm leading-normal text-muted-foreground">
              {displayBody(parts.quoted)}
            </p>
            <button
              type="button"
              class="mt-1 text-xs text-muted-foreground underline focus-visible:ring-2 focus-visible:ring-ring"
              data-show-quoted
              onclick={() => {
                const id = previewHit.message_id;
                quotedOpen = { ...quotedOpen, [id]: !quotedOpen[id] };
              }}>{t("hideQuoted")}</button
            >
          {:else}
            <button
              type="button"
              class="mt-1 text-xs text-muted-foreground underline focus-visible:ring-2 focus-visible:ring-ring"
              data-show-quoted
              onclick={() => {
                const id = previewHit.message_id;
                quotedOpen = { ...quotedOpen, [id]: !quotedOpen[id] };
              }}>{t("showQuoted")}</button
            >
          {/if}
        {/if}
      {:else}
        <p class="mt-2 whitespace-pre-wrap break-words text-sm leading-normal">
          {displayBody(previewBody)}
        </p>
      {/if}
      {#key previewHit.message_id}
        <CasAttach items={previewHit.attachments || []} showToast={onToast} />
      {/key}
    {:else}
      <div class="text-sm text-muted-foreground" data-search-preview-empty>
        <p>{t("searchPreviewEmpty")}</p>
        <Button
          size="sm"
          variant="ghost"
          class="mt-2 px-0"
          onclick={() => document.getElementById("q")?.focus()}
          >{t("searchPreviewFocusQuery")}</Button
        >
      </div>
    {/if}
  </div>
</div>
