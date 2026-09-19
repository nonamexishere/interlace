<script lang="ts">
  import type { TimelineRow } from "./api";
  import { localDay, utcTime } from "./formatTime";
  import { splitUrls } from "./linkify";
  import LinkifyBody from "./LinkifyBody.svelte";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import CasAttach from "$lib/CasAttach.svelte";
  import { displayBody, isMailRow, platformLabel, splitQuotedBody } from "./TimelineMail";
  import { t } from "$lib/i18n";

  let {
    windowedDayGroups,
    spacerTop,
    spacerBottom,
    tlIndex,
    quotedOpen,
    measureTlRow,
    isGroupedFollower,
    onSelectIndex,
    selectedIds = new Set<number>(),
    onContextMenu,
    toggleQuoted,
    openUrl,
    showToast,
    showLoadOlder = false,
    tlLoading = false,
    onPrepend,
    findQ = "",
    lastReadMessageId = undefined,
  }: {
    windowedDayGroups: {
      key: string;
      label: string;
      rows: { row: TimelineRow; index: number }[];
    }[];
    spacerTop: number;
    spacerBottom: number;
    tlIndex: number;
    quotedOpen: Record<number, boolean>;
    measureTlRow: (node: HTMLElement, orig: number) => { update: (n: number) => void; destroy: () => void };
    isGroupedFollower: (i: number) => boolean;
    onSelectIndex: (index: number, shiftKey?: boolean) => void;
    selectedIds?: Set<number>;
    onContextMenu: (e: MouseEvent, row: TimelineRow) => void;
    toggleQuoted: (messageId: number, e: Event) => void;
    openUrl: (url: string) => void;
    showToast: (message: string) => void;
    showLoadOlder?: boolean;
    tlLoading?: boolean;
    onPrepend?: () => void;
    findQ?: string;
    lastReadMessageId?: number;
  } = $props();
</script>

{#if showLoadOlder}
  <Button
    variant="outline"
    size="sm"
    class="mb-4 mt-4"
    data-load-older
    disabled={tlLoading}
    onclick={() => !tlLoading && onPrepend?.()}
    >Load older</Button
  >
{/if}
<ol class="min-w-0">
  {#if spacerTop > 0}
    <li class="timeline-spacer-top pointer-events-none" style="height: {spacerTop}px" aria-hidden="true"></li>
  {/if}
  {#each windowedDayGroups as group (group.rows[0]?.index ?? group.key)}
    <li class="day-group min-w-0">
      {#if group.rows[0]?.row.sent_at && localDay(group.rows[0].row.sent_at, group.rows[0].row.platform)}
        <h3 class="day-heading mb-2 text-center text-xs font-medium text-muted-foreground">
          {group.label}
        </h3>
      {/if}
      <div>
        {#each group.rows as item (item.index)}
          <div class="flex min-w-0 pb-2" data-tl-index={item.index} use:measureTlRow={item.index}>
            <div class="flex w-fit max-w-[94%] flex-col" class:ml-auto={item.row.from_me}>
            {#if lastReadMessageId != null && item.row.message_id === lastReadMessageId}
              <p class="px-1 pb-1 text-xs text-muted-foreground">{t("lastTime")}</p>
            {/if}
            <article
              class="flex min-w-0 max-w-[94%] cursor-pointer flex-col gap-2 rounded-2xl px-3 py-2 text-left focus-visible:ring-2 focus-visible:ring-ring {item.index ===
              tlIndex
                ? 'ring-2 ring-ring'
                : selectedIds.has(item.row.message_id)
                  ? 'ring-1 ring-ring'
                  : ''}"
              class:bubble-me={item.row.from_me}
              class:bubble-them={!item.row.from_me}
              class:ml-auto={item.row.from_me}
              data-from-me={item.row.from_me}
              data-grouped={isGroupedFollower(item.index) || undefined}
              tabindex="0"
              aria-label={`${utcTime(item.row.sent_at, item.row.platform)} ${displayBody(item.row.body_text || item.row.subject || "").slice(0, 80)}`}
              onclick={(e) => onSelectIndex(item.index, e.shiftKey)}
              oncontextmenu={(e) => onContextMenu(e, item.row)}
            >
              {#if !isGroupedFollower(item.index)}
                <p
                  class="caption flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground"
                  data-bubble-meta
                >
                  <time>{utcTime(item.row.sent_at, item.row.platform)}</time>
                  <Badge
                    variant="outline"
                    class="platform-chip rounded-full border-border/80 bg-background/60 px-1.5 py-px text-[0.65rem] font-medium leading-none text-muted-foreground"
                    data-platform-chip
                    >{platformLabel(item.row.platform)}</Badge
                  >
                  {#if isMailRow(item.row) && item.row.from_me}
                    <span class="text-xs text-muted-foreground">You</span>
                  {/if}
                </p>
              {/if}
              <div data-bubble-body>
                {#if isMailRow(item.row)}
                  {#if (item.row.subject ?? "").trim()}
                    <p class="mail-subject text-sm font-medium text-foreground">
                      <LinkifyBody text={item.row.subject ?? ""} {splitUrls} {openUrl} {findQ} />
                    </p>
                  {/if}
                  {@const names = item.row.labels ?? []}
                  {@const visibleLabels = names.slice(0, 3)}
                  {#if names.length}
                    <div
                      class="mail-labels flex min-w-0 flex-nowrap items-center gap-1 overflow-hidden"
                      data-mail-labels
                    >
                      {#if visibleLabels[0]}
                        {@const name = visibleLabels[0]}
                        <Badge
                          variant="outline"
                          class="mail-label-chip min-w-0 truncate rounded-full border-border/80 bg-background/60 px-1.5 py-px text-[0.65rem] font-medium leading-none text-muted-foreground"
                          >{name}</Badge
                        >
                      {/if}
                      {#if visibleLabels[1]}
                        {@const name = visibleLabels[1]}
                        <Badge
                          variant="outline"
                          class="mail-label-chip min-w-0 truncate rounded-full border-border/80 bg-background/60 px-1.5 py-px text-[0.65rem] font-medium leading-none text-muted-foreground"
                          >{name}</Badge
                        >
                      {/if}
                      {#if visibleLabels[2]}
                        {@const name = visibleLabels[2]}
                        <Badge
                          variant="outline"
                          class="mail-label-chip min-w-0 truncate rounded-full border-border/80 bg-background/60 px-1.5 py-px text-[0.65rem] font-medium leading-none text-muted-foreground"
                          >{name}</Badge
                        >
                      {/if}
                      {#if names.length > 3}
                        <span class="shrink-0 text-[0.65rem] text-muted-foreground"
                          >+{names.length - 3}</span
                        >
                      {/if}
                    </div>
                  {/if}
                  {@const parts = splitQuotedBody(item.row.body_text || "")}
                  {#if parts.main || !parts.quoted}
                    <p class="whitespace-pre-wrap break-words text-sm leading-normal text-foreground">
                      <LinkifyBody text={displayBody(parts.main)} {splitUrls} {openUrl} {findQ} />
                    </p>
                  {/if}
                  {#if parts.quoted}
                    {#if quotedOpen[item.row.message_id]}
                      <p class="mt-1 whitespace-pre-wrap break-words text-sm leading-normal text-muted-foreground">
                        <LinkifyBody text={displayBody(parts.quoted)} {splitUrls} {openUrl} {findQ} />
                      </p>
                      <button
                        type="button"
                        class="mt-1 text-xs text-muted-foreground underline focus-visible:ring-2 focus-visible:ring-ring"
                        data-show-quoted
                        onclick={(e) => toggleQuoted(item.row.message_id, e)}
                        >Hide quoted</button
                      >
                    {:else}
                      <button
                        type="button"
                        class="mt-1 text-xs text-muted-foreground underline focus-visible:ring-2 focus-visible:ring-ring"
                        data-show-quoted
                        onclick={(e) => toggleQuoted(item.row.message_id, e)}
                        >Show quoted</button
                      >
                    {/if}
                  {/if}
                {:else}
                  <p class="whitespace-pre-wrap break-words text-sm leading-normal text-foreground">
                    <LinkifyBody
                      text={displayBody(item.row.body_text || item.row.subject || "")}
                      {splitUrls}
                      {openUrl}
                      {findQ}
                    />
                  </p>
                {/if}
              </div>
              <CasAttach data-bubble-attach flush={true} items={item.row.attachments || []} {showToast} />
            </article>
            </div>
          </div>
        {/each}
      </div>
    </li>
  {/each}
  {#if spacerBottom > 0}
    <li class="timeline-spacer-bottom pointer-events-none" style="height: {spacerBottom}px" aria-hidden="true"></li>
  {/if}
</ol>
