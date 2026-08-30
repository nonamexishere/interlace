<script lang="ts">
  import { tick } from "svelte";
  import { api, type Identity, type Person, type PersonConversation, type TimelineRow } from "./api";
  import TimelineFilters from "./TimelineFilters.svelte";
  import TimelineList from "./TimelineList.svelte";
  import { platformLabel } from "./TimelineMail";
  import { writeIncludeGroupsPref } from "./PeoplePrefs";
  import { findCount, findHitIndices, onFindKey, snapFindHit, stepFindIndex } from "./findHighlight";
  import { jumpToLocalDay, nearestVisibleTlIndex } from "./jumpDay";
  import { Input } from "$lib/components/ui/input/index.js";
  import { t } from "$lib/i18n";

  let {
    selectedId = $bindable<number | null>(null),
    personTitle = $bindable("Select a person"),
    identities = $bindable<Identity[]>([]),
    includeGroups = $bindable(false),
    tlIndex = $bindable(0),
    visibleTlIndices = $bindable<number[]>([]),
    showPersonChrome = $bindable(false),
    density,
    persistLastPerson,
    friendly,
    showErr,
    showToast,
    openUrl,
    onImport,
    onSearchFromBubble,
    onCopyFail,
    onFocusInspector,
  }: {
    selectedId?: number | null;
    personTitle?: string;
    identities?: Identity[];
    includeGroups?: boolean;
    tlIndex?: number;
    visibleTlIndices?: number[];
    showPersonChrome?: boolean;
    density: string;
    persistLastPerson: (id: number) => void;
    friendly: (raw: string) => string;
    showErr: (e: unknown) => void;
    showToast: (message: string) => void;
    openUrl: (url: string) => void;
    onImport: () => void;
    onSearchFromBubble: () => void;
    onCopyFail: () => void;
    onFocusInspector: () => void;
  } = $props();

  let timeline = $state<TimelineRow[]>([]);
  let conversations = $state<PersonConversation[]>([]);
  let selectedConversationId = $state<number | null>(null);
  let platformFilter = $state("all");
  let kindFilter = $state("all");
  let tlLoading = $state(false);
  let tlAppending = $state(false);
  let tlError = $state("");
  let tlGen = 0;
  let findQ = $state(""), jumpDay = $state("");
  let quotedOpen = $state<Record<number, boolean>>({});
  let list: {
    ensureTlIndexVisible: (index: number) => void;
    applyOpenPersonWindow: (gen: number, currentGen: () => number) => void;
    shiftHeightsForPrepend: (n: number) => void;
    resetHeights: () => void;
    preserveScrollAfterPrepend: (prevHeight: number) => void;
    stopPin: () => void;
    estimateScrollToIndex: (index: number) => void;
    pinDayAtTop: (filteredPos: number) => void;
    closeCopy: () => void;
  } | undefined = $state();

  const KIND_ORDER = ["dm", "email_thread", "group"] as const;

  const availablePlatforms = $derived.by(() => {
    const set = new Set<string>();
    for (const c of conversations) {
      if (kindFilter !== "all" && (c.kind ?? "").trim() !== kindFilter) continue;
      const p = (c.platform ?? "").trim();
      if (p) set.add(p);
    }
    for (const row of timeline) {
      if (kindFilter !== "all" && (row.conversation_kind ?? "").trim() !== kindFilter) {
        continue;
      }
      const p = (row.platform ?? "").trim();
      if (p) set.add(p);
    }
    return [...set].sort();
  });

  const availableKinds = $derived.by(() => {
    const set = new Set<string>();
    for (const c of conversations) {
      if (platformFilter !== "all" && (c.platform ?? "").trim() !== platformFilter) {
        continue;
      }
      const k = (c.kind ?? "").trim();
      if (k) set.add(k);
    }
    for (const row of timeline) {
      if (platformFilter !== "all" && (row.platform ?? "").trim() !== platformFilter) {
        continue;
      }
      const k = (row.conversation_kind ?? "").trim();
      if (k) set.add(k);
    }
    const known = KIND_ORDER.filter((k) => set.has(k));
    const rest = [...set].filter((k) => !(KIND_ORDER as readonly string[]).includes(k)).sort();
    return [...known, ...rest];
  });

  $effect(() => {
    if (platformFilter !== "all" && !availablePlatforms.includes(platformFilter)) {
      platformFilter = "all";
    }
  });
  $effect(() => {
    if (kindFilter !== "all" && !availableKinds.includes(kindFilter)) {
      kindFilter = "all";
    }
  });

  const filteredTimeline = $derived(
    timeline
      .map((row, index) => ({ row, index }))
      .filter(
        (item) =>
          (platformFilter === "all" || item.row.platform === platformFilter) &&
          (kindFilter === "all" || item.row.conversation_kind === kindFilter),
      ),
  );

  $effect(() => {
    visibleTlIndices = filteredTimeline.map((item) => item.index);
  });

  $effect(() => {
    const visible = visibleTlIndices;
    if (tlIndex < 0) return;
    if (!visible.length) return;
    if (!visible.includes(tlIndex)) {
      tlIndex = nearestVisibleTlIndex(tlIndex, visible);
    }
  });

  function oldestSentAt(rows: TimelineRow[]): string | null {
    for (const row of rows) {
      if (row.sent_at) return row.sent_at;
    }
    return null;
  }

  const oldestCursor = $derived(oldestSentAt(timeline));
  const selectedConversation = $derived(
    conversations.find((c) => c.id === selectedConversationId),
  );

  function conversationLabel(title: string | null | undefined, platform: string | null | undefined) {
    if (
      !(title ?? "").trim() ||
      (title ?? "").trim().toLowerCase() === personTitle.trim().toLowerCase()
    ) {
      return platformLabel(platform);
    }
    return title;
  }

  export async function selectPerson(id: number, append = false, keepConversation = false, groups = includeGroups) {
    includeGroups = groups;
    if (append && tlLoading) return;
    const before = append ? oldestSentAt(timeline) : null;
    if (append && !before) return;
    if (!append) persistLastPerson(id);

    if (!append && id !== selectedId) {
      showPersonChrome = false;
      platformFilter = "all";
      kindFilter = "all";
      findQ = "";
    }
    selectedId = id;
    if (!append && !keepConversation) {
      selectedConversationId = null;
    }
    const gen = ++tlGen;
    tlAppending = append;
    tlLoading = true;
    tlError = "";
    list?.stopPin();
    try {
      const show = await api.personShow(id);
      if (gen !== tlGen) return;
      personTitle = show.display_name || `person ${id}`;
      identities = show.identities || [];
      if (!append && !keepConversation) {
        conversations = await api.personConversations({ id, includeGroups: groups });
        if (gen !== tlGen) return;
      }
      const page = await api.personTimeline({
        id,
        includeGroups: groups,
        limit: 80,
        before,
        conversationId: selectedConversationId,
      });
      if (gen !== tlGen) return;
      const pane = document.getElementById("person-timeline");
      const prevHeight = pane?.scrollHeight ?? 0;
      const chrono = page.toReversed();
      if (append) {
        list?.shiftHeightsForPrepend(chrono.length);
      } else {
        list?.resetHeights();
      }
      timeline = append ? chrono.concat(timeline) : chrono;
      tlIndex = append ? tlIndex + chrono.length : Math.max(0, chrono.length - 1);
      if (append) {
        await tick();
        if (gen !== tlGen) return;
        list?.preserveScrollAfterPrepend(prevHeight);
      } else {
        // Loading line still in the pane makes one rAF land short after wrap.
        tlLoading = false;
        await tick();
        if (gen !== tlGen) return;
        const sc = document.getElementById("person-timeline");
        if (sc) {
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              if (gen !== tlGen) return;
              if (findQ) { list?.ensureTlIndexVisible(tlIndex); return; }
              sc.scrollTop = sc.scrollHeight;
              list?.applyOpenPersonWindow(gen, () => tlGen);
            });
          });
        }
      }
    } catch (e) {
      if (gen === tlGen) {
        tlError = friendly(e instanceof Error ? e.message : String(e ?? ""));
        if (!append) timeline = [];
      }
    } finally {
      if (gen === tlGen) {
        tlLoading = false;
        tlAppending = false;
      }
    }
  }

  export async function openPersonAtMessage(
    personId: number,
    messageId: number,
    sentAt?: string | null,
  ) {
    showPersonChrome = false;
    platformFilter = "all";
    kindFilter = "all";
    findQ = "";
    selectedId = personId;
    persistLastPerson(personId);
    selectedConversationId = null;
    const gen = ++tlGen;
    tlAppending = false;
    tlLoading = true;
    tlError = "";
    list?.stopPin();
    try {
      const show = await api.personShow(personId);
      if (gen !== tlGen) return;
      personTitle = show.display_name || `person ${personId}`;
      identities = show.identities || [];
      conversations = await api.personConversations({
        id: personId,
        includeGroups,
      });
      if (gen !== tlGen) return;

      const pageLimit = 200;
      const maxPages = 80;
      const seekAt = (sentAt ?? "").trim();
      let loaded: TimelineRow[] = [];
      let before: string | null = seekAt ? `${seekAt}~` : null;
      for (let page = 0; page < maxPages; page++) {
        const batch = await api.personTimeline({
          id: personId,
          includeGroups,
          limit: pageLimit,
          before,
          conversationId: null,
        });
        if (gen !== tlGen) return;
        if (batch.length === 0) break;
        const chrono = batch.toReversed();
        loaded = page === 0 ? chrono : chrono.concat(loaded);
        if (loaded.some((r) => r.message_id === messageId)) break;
        const nextBefore = oldestSentAt(loaded);
        if (!nextBefore || batch.length < pageLimit) break;
        before = nextBefore;
      }
      if (gen !== tlGen) return;

      timeline = loaded;
      list?.resetHeights();
      const idx = loaded.findIndex((r) => r.message_id === messageId);
      if (idx < 0) {
        tlIndex = -1;
        showErr(
          "Could not find that message on the person timeline (too far back or not in this view).",
        );
        return;
      }
      tlIndex = idx;
      list?.estimateScrollToIndex(tlIndex);
      tlLoading = false;
      await tick();
      if (gen !== tlGen) return;
      list?.ensureTlIndexVisible(tlIndex);
      requestAnimationFrame(() => {
        if (gen !== tlGen) return;
        list?.ensureTlIndexVisible(tlIndex);
      });
    } catch (e) {
      if (gen === tlGen) {
        tlError = friendly(e instanceof Error ? e.message : String(e ?? ""));
        timeline = [];
      }
    } finally {
      if (gen === tlGen) tlLoading = false;
    }
  }

  async function pickConversation(conversationId: number | null) {
    if (!selectedId) return;
    selectedConversationId = conversationId;
    const keepConversation = true;
    await selectPerson(selectedId, false, keepConversation);
  }

  export function ensureTlIndexVisible(index: number) {
    list?.ensureTlIndexVisible(index);
  }

  function stepFind(dir: 1 | -1) {
    const next = stepFindIndex(filteredTimeline, findQ, tlIndex, dir, quotedOpen);
    if (next != null) { tlIndex = next; list?.ensureTlIndexVisible(next); }
  }

  $effect(() => {
    const hits = findHitIndices(filteredTimeline, findQ, quotedOpen);
    const snap = snapFindHit(hits, tlIndex);
    if (snap != null) { tlIndex = snap; list?.ensureTlIndexVisible(snap); }
  });

  function onPaneFindKey(e: KeyboardEvent) {
    onFindKey(e, findQ, (q) => (findQ = q), stepFind);
  }

  function goToJumpDay() {
    void jumpToLocalDay({
      key: jumpDay, filteredTimeline: () => filteredTimeline, selectedId,
      tlLoading: () => tlLoading, oldestCursor: () => oldestCursor, timelineLength: () => timeline.length,
      selectPerson: (id, append) => selectPerson(id, append),
      scrollToPos: (pos) => { const item = filteredTimeline[pos]; if (item) tlIndex = item.index; list?.stopPin(); list?.pinDayAtTop(pos); },
    });
  }

  export function closeCopyMenu() {
    list?.closeCopy();
  }
</script>

<div class="flex min-h-0 min-w-0 flex-1 flex-col">
  <div class="relative z-20 shrink-0 bg-background px-4 pt-4">
    <div class="mb-3 flex items-baseline justify-between gap-3">
      <h1 class="text-xl font-semibold tracking-tight">
        <button
          type="button"
          class="text-left focus-visible:ring-2 focus-visible:ring-ring"
          onclick={() => (
            (showPersonChrome = !showPersonChrome),
            showPersonChrome && onFocusInspector()
          )}
        >
          {personTitle}
        </button>
      </h1>
      {#if false}
        {#if selectedId && conversations.length > 1}
          <details data-conversation-switcher class="relative z-20 min-w-0 max-w-[16rem]">
            <summary
              class="cursor-pointer truncate rounded-md border border-border px-2 py-1 text-sm focus-visible:ring-2 focus-visible:ring-ring"
            >
              {#if selectedConversationId === null}
                All
              {:else}
                {conversationLabel(selectedConversation?.title, selectedConversation?.platform)}
              {/if}
            </summary>
            <ul
              class="absolute right-0 z-10 mt-1 min-w-[14rem] space-y-0.5 rounded-md border border-border bg-background p-1 shadow-md"
            >
              <li>
                <button
                  type="button"
                  class="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring {selectedConversationId ===
                  null
                    ? 'bg-accent'
                    : ''}"
                  onclick={() => pickConversation(null)}
                >
                  All
                </button>
              </li>
              {#each conversations as conv}
                <li>
                  <button
                    type="button"
                    class="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring {selectedConversationId ===
                    conv.id
                      ? 'bg-accent'
                      : ''}"
                    onclick={() => pickConversation(conv.id)}
                  >
                    <span>{conversationLabel(conv.title, conv.platform)}</span>
                    <span class="mt-0.5 block truncate text-xs font-normal text-muted-foreground">
                      {conv.platform}{conv.last_at ? ` · ${conv.last_at}` : ""}
                    </span>
                  </button>
                </li>
              {/each}
            </ul>
          </details>
        {/if}
      {/if}
    </div>
    {#if selectedId}
      <TimelineFilters
        {availablePlatforms}
        {availableKinds}
        bind:platformFilter
        bind:kindFilter
      />
      <div class="mb-3 flex items-center gap-2">
        <Input id="tl-find" data-tl-find type="search" bind:value={findQ} placeholder={t("findInThread")} aria-label={t("findInThread")} autocomplete="off" class="h-8 min-w-0 flex-1" onkeydown={onPaneFindKey} />
        <Input type={"date"} bind:value={jumpDay} aria-label={t("jumpToDay")} class="h-8 w-auto shrink-0" onchange={goToJumpDay} />
        {#if findQ}
          <span data-tl-hit-count class="shrink-0 text-xs tabular-nums text-muted-foreground">{findCount(filteredTimeline, findQ, tlIndex, quotedOpen)}</span>
        {/if}
      </div>
    {/if}
  </div>
  <TimelineList
    bind:this={list}
    {timeline}
    {filteredTimeline}
    {selectedId}
    bind:tlIndex bind:quotedOpen
    {tlLoading}
    {tlAppending}
    {tlError}
    bind:includeGroups
    {oldestCursor}
    {density}
    onRetry={() => selectedId && selectPerson(selectedId)}
    onPrepend={() => {
      const append = !!selectedId;
      if (append) void selectPerson(selectedId, append);
    }}
    {onImport}
    onShowAll={() => {
      platformFilter = "all";
      kindFilter = "all";
    }}
    onIncludeGroups={() => {
      if (!selectedId) return;
      includeGroups = true;
      writeIncludeGroupsPref(true);
      void selectPerson(selectedId);
    }}
    {openUrl}
    {showToast}
    {onSearchFromBubble}
    {onCopyFail}
    {findQ}
  />
  <p class="shrink-0 bg-background px-4 pb-4 pt-2 text-xs text-muted-foreground">
    Bodies are text only. Day headings follow the Mac timezone. <kbd class="rounded border border-border px-1">j</kbd>/<kbd
      class="rounded border border-border px-1">k</kbd
    >
    move.
    <kbd class="rounded border border-border px-1">/</kbd> filters people.
  </p>
</div>
