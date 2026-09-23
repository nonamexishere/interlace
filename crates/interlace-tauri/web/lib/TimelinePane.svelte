<script lang="ts">
  import { tick } from "svelte";
  import { api, type Attachment, type Identity, type Person, type PersonConversation, type TimelineRow } from "./api";
  import TimelineFilters from "./TimelineFilters.svelte";
  import TimelineLightbox from "./TimelineLightbox.svelte";
  import TimelineList from "./TimelineList.svelte";
  import { collectOlderThreadRows, readThreadPhoto, threadImages, threadIndex, type ThreadTarget } from "./threadWalk";
  import { platformLabel, rowMatchesAttachKind } from "./TimelineMail";
  import { rangeIds, selectionLive } from "./TimelineSelect";
  import { lastReadFor, persistLastRead as writePersonLastRead, writeIncludeGroupsPref } from "./PeoplePrefs";
  import { findCount, findHitIndices, onFindKey, snapFindHit, stepFindIndex } from "./findHighlight";
  import { applyJumpScrollPos, jumpToLocalDay, jumpToMessageId, nearestVisibleTlIndex, TIMELINE_PAGE_LIMIT } from "./jumpDay";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import PersonMediaDialog from "./PersonMediaDialog.svelte";
  import { t } from "$lib/i18n";
  import {
    clearVoiceHost,
    consumeSeekEnded,
    nextPlayableVoice,
    publishVoice,
    startVoiceHost,
    warmVoiceUrls,
  } from "./voiceHost";

  let {
    selectedId = $bindable<number | null>(null),
    personTitle = $bindable("Select a person"),
    identities = $bindable<Identity[]>([]),
    includeGroups = $bindable(false),
    tlIndex = $bindable(0),
    visibleTlIndices = $bindable<number[]>([]),
    showPersonChrome = $bindable(false),
    selectedConversationId = $bindable<number | null>(null),
    timeline = $bindable<TimelineRow[]>([]),
    conversations = $bindable<PersonConversation[]>([]),
    archive_id = "",
    density,
    persistLastPerson,
    friendly,
    showErr,
    showToast,
    openUrl,
    onImport,
    onSearchFromBubble,
    onSearchThisConversation,
    onCopyFail,
    onFocusInspector,
    loadActivityYears,
  }: {
    selectedId?: number | null;
    personTitle?: string;
    identities?: Identity[];
    includeGroups?: boolean;
    tlIndex?: number;
    visibleTlIndices?: number[];
    showPersonChrome?: boolean;
    selectedConversationId?: number | null;
    timeline?: TimelineRow[];
    conversations?: PersonConversation[];
    archive_id?: string;
    density: string;
    persistLastPerson: (id: number) => void;
    friendly: (raw: string) => string;
    showErr: (e: unknown) => void;
    showToast: (message: string) => void;
    openUrl: (url: string) => void;
    onImport: () => void;
    onSearchFromBubble: () => void;
    onSearchThisConversation: (seed: { id: number; title: string; kind: string }) => void;
    onCopyFail: () => void;
    onFocusInspector: () => void;
    loadActivityYears: (groups: boolean) => void;
  } = $props();

  let platformFilter = $state("all");
  let kindFilter = $state("all");
  let attachKindFilter = $state("all");
  let fromMeFilter = $state("all");
  let tlLoading = $state(false);
  let tlAppending = $state(false);
  let tlError = $state("");
  let tlGen = 0;
  let threadTarget = $state<ThreadTarget | null>(null);
  let threadSrc = $state<string | null>(null);
  let threadBroken = $state<string[]>([]);
  let threadOlderExhausted = $state(false);
  let threadWalkGen = 0;
  let threadPrevToken = 0;
  let threadPrevBusy = false;
  const threadPhotoCache = new Map<string, string | null>();

  function invalidateThreadWalk() {
    threadWalkGen += 1;
    threadPrevToken += 1;
    threadPrevBusy = false;
  }
  let findQ = $state(""), jumpDay = $state(""), jumpGen = 0, dayPin = false;
  let galleryOpen = $state(false);
  let voiceHostEl = $state<HTMLAudioElement | null>(null);
  let quotedOpen = $state<Record<number, boolean>>({});
  let list: {
    ensureTlIndexVisible: (index: number) => void;
    applyOpenPersonWindow: (gen: number, currentGen: () => number) => void;
    shiftHeightsForPrepend: (n: number) => void;
    resetHeights: () => void;
    preserveScrollAfterPrepend: (prevHeight: number) => void;
    holdAnchorAfterPrepend: (addedCount: number, apply: () => void) => Promise<void>;
    stopPin: () => void;
    estimateScrollToIndex: (index: number) => void;
    pinJump: (index: number) => void;
    pinDayAtTop: (filteredPos: number) => void;
    closeCopy: () => void; scrollToLatest: () => void; copySelected: () => void;
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
          (kindFilter === "all" || item.row.conversation_kind === kindFilter) &&
          (attachKindFilter === "all" || rowMatchesAttachKind(item.row, attachKindFilter)) &&
          (fromMeFilter === "all" ||
            (fromMeFilter === "me" && item.row.from_me === true) ||
            (fromMeFilter === "them" && item.row.from_me === false)),
      ),
  );

  $effect(() => {
    visibleTlIndices = filteredTimeline.map((item) => item.index);
  });

  function onVoiceHostEnded() {
    if (consumeSeekEnded()) return;
    const host = voiceHostEl;
    if (!host) return;
    const message_id = Number(host.dataset.voiceMsg || "0");
    const key = host.dataset.voiceKey || "";
    const next = nextPlayableVoice(filteredTimeline, message_id, key);
    if (!next) {
      publishVoice({ playing: false });
      return;
    }
    startVoiceHost(host, next.message_id, next.key, next.casDataUrl, filteredTimeline);
  }

  function stopVoiceIfFilteredOut() {
    const host = voiceHostEl;
    if (!host) return;
    const message_id = Number(host.dataset.voiceMsg || "0");
    if (!message_id) return;
    const live = filteredTimeline.some((item) => item.row.message_id === message_id);
    if (live) return;
    host.pause();
    host.src = "";
    publishVoice({ playing: false, messageId: 0, key: "" });
  }

  $effect(() => {
    warmVoiceUrls(filteredTimeline);
    stopVoiceIfFilteredOut();
  });

  $effect(() => {
    const host = voiceHostEl;
    if (!host) return;
    const sync = () => {
      publishVoice({
        time: host.currentTime || 0,
        duration: Number.isFinite(host.duration) ? host.duration : 0,
        playing: !host.paused && !host.ended,
      });
    };
    host.addEventListener("timeupdate", sync);
    host.addEventListener("play", sync);
    host.addEventListener("pause", sync);
    host.addEventListener("loadedmetadata", sync);
    host.addEventListener("durationchange", sync);
    return () => {
      host.removeEventListener("timeupdate", sync);
      host.removeEventListener("play", sync);
      host.removeEventListener("pause", sync);
      host.removeEventListener("loadedmetadata", sync);
      host.removeEventListener("durationchange", sync);
    };
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

  let lastReadEpoch = $state(0);
  let loadedArchiveId = $state("");
  let selectedIds = $state(new Set<number>());
  let anchorId = $state<number | null>(null);
  const liveSelectedIds = $derived(
    selectionLive(loadedArchiveId, archive_id) ? selectedIds : new Set<number>(),
  );

  let seenArchiveId = archive_id;
  $effect(() => {
    if (seenArchiveId === archive_id) return;
    seenArchiveId = archive_id;
    ++tlGen;
    selectedIds = new Set();
    anchorId = null;
  });

  export function extendSelection(targetIndex: number) {
    const target = filteredTimeline.find((item) => item.index === targetIndex)?.row ?? timeline[targetIndex];
    if (!target) return;
    if (anchorId == null) {
      const cur = filteredTimeline.find((item) => item.index === tlIndex)?.row ?? timeline[tlIndex];
      if (cur) anchorId = cur.message_id;
    }
    selectedIds = rangeIds(filteredTimeline, anchorId, target.message_id);
  }
  const lastReadMessageId = $derived.by(() => {
    void lastReadEpoch;
    if (selectedId == null) return undefined;
    if (loadedArchiveId !== archive_id) return undefined;
    return lastReadFor(archive_id, selectedId);
  });

  export function persistLastRead(index: number) {
    if (loadedArchiveId !== archive_id) return;
    const row = timeline[index];
    if (!row || selectedId == null) return;
    writePersonLastRead(archive_id, selectedId, row.message_id);
    lastReadEpoch += 1;
  }

  const oldestCursor = $derived(oldestSentAt(timeline));
  const threadSteps = $derived(threadImages(filteredTimeline).filter((step) => !threadBroken.includes(step.hash)));
  const threadAt = $derived(threadTarget ? threadIndex(threadSteps, threadTarget) : -1);
  const nextAtEnd = $derived(threadAt < 0 || threadAt >= threadSteps.length - 1);
  const prevExhausted = $derived(threadAt < 0 ? true : threadAt === 0 && (!oldestCursor || threadOlderExhausted));
  const threadAlt = $derived.by(() => {
    if (!threadTarget) return "image";
    const pools = [filteredTimeline.map((item) => item.row), timeline];
    for (const pool of pools) {
      for (const row of pool) {
        if (row.message_id !== threadTarget.message_id) continue;
        for (const a of row.attachments ?? []) {
          if (a.id === threadTarget.attachment_id) return a.filename || "image";
        }
      }
    }
    return "image";
  });
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
    if (!append) clearVoiceHost(voiceHostEl);
    if (!append) threadTarget = null
    if (!append) threadSrc = null
    if (!append) threadOlderExhausted = false
    if (!append) invalidateThreadWalk()
    const loadArchiveId = archive_id;
    includeGroups = groups;
    if (append && tlLoading) return;
    const before = append ? oldestSentAt(timeline) : null;
    if (append && !before) return;
    if (!append) { dayPin = false; jumpGen++; persistLastPerson(id); }

    if (!append && id !== selectedId) {
      selectedIds = new Set();
      anchorId = null;
      showPersonChrome = false;
      platformFilter = "all";
      kindFilter = "all";
      attachKindFilter = "all";
      fromMeFilter = "all";
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
      personTitle = show.display_name || "person " + id;
      identities = show.identities || [];
      if (!append && !keepConversation) {
        conversations = await api.personConversations({ id, includeGroups: groups });
        if (gen !== tlGen) return;
      }
      const page = await api.personTimeline({
        id,
        includeGroups: groups,
        limit: TIMELINE_PAGE_LIMIT,
        before,
        conversationId: selectedConversationId,
        ...(attachKindFilter !== "all" ? { attachKind: attachKindFilter } : {}),
      });
      if (gen !== tlGen) return;
      const pane = document.getElementById("person-timeline");
      const prevHeight = pane?.scrollHeight ?? 0;
      const chrono = page.toReversed();
      let added = chrono;
      if (append) {
        const seen = new Set(timeline.map((row) => row.message_id));
        added = chrono.filter((row) => !seen.has(row.message_id));
        if (added.length === 0) {
          list?.abandonPrependShift();
          return;
        }
        threadOlderExhausted = false;
        list?.shiftHeightsForPrepend(added.length);
      } else {
        list?.resetHeights();
      }
      timeline = append ? added.concat(timeline) : chrono;
      if (loadArchiveId === archive_id) loadedArchiveId = archive_id;
      if (append) tlIndex += added.length;
      else tlIndex = Math.max(0, chrono.length - 1);
      if (append) {
        await tick();
        if (gen !== tlGen) {
          list?.abandonPrependShift();
          return;
        }
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
    clearVoiceHost(voiceHostEl);
    threadTarget = null
    threadSrc = null
    threadOlderExhausted = false
    invalidateThreadWalk()
    const loadArchiveId = archive_id;
    showPersonChrome = false;
    platformFilter = "all";
    kindFilter = "all";
    attachKindFilter = "all";
    fromMeFilter = "all";
    findQ = ""; dayPin = false; jumpGen++;
    selectedIds = new Set([messageId]);
    anchorId = messageId;
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
      personTitle = show.display_name || "person " + personId;
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
          ...(attachKindFilter !== "all" ? { attachKind: attachKindFilter } : {}),
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
      if (loadArchiveId === archive_id) loadedArchiveId = archive_id;
      selectedIds = new Set([messageId]);
      anchorId = messageId;
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
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (gen !== tlGen) return;
          list?.pinJump(tlIndex);
        });
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
    const snap = dayPin ? null : snapFindHit(hits, tlIndex);
    if (snap != null) { tlIndex = snap; list?.ensureTlIndexVisible(snap); }
  });

  function onPaneFindKey(e: KeyboardEvent) {
    onFindKey(e, findQ, (q) => (findQ = q), stepFind);
  }

  function goToLastRead() {
    const messageId = lastReadMessageId;
    if (messageId == null || selectedId == null) return;
    selectedIds = new Set([messageId]);
    anchorId = messageId;
    const gen = ++jumpGen, id = selectedId, key = jumpDay;
    void jumpToMessageId({
      key, gen, selectedId: id, messageId,
      currentSelectedId: () => selectedId, currentJumpDay: () => jumpDay, currentGen: () => jumpGen,
      filteredTimeline: () => filteredTimeline,
      timeline: () => timeline,
      tlLoading: () => tlLoading, oldestCursor: () => oldestCursor, timelineLength: () => timeline.length,
      selectPerson: async (pid, append) => { if (selectedId !== id || jumpDay !== key || jumpGen !== gen) return; return selectPerson(pid, append); },
      scrollToPos: () => {},
      setTlIndex: (n) => { tlIndex = n; },
      ensureTlIndexVisible: (n) => list?.ensureTlIndexVisible(n),
    });
  }

  export function jumpToDayKey(day: string) {
    const key = (day ?? "").trim();
    if (!key || selectedId == null) return;
    jumpDay = key;
    goToJumpDay();
  }

  function goToJumpDay() {
    const gen = ++jumpGen, id = selectedId, key = jumpDay; dayPin = true;
    void jumpToLocalDay({
      key, gen, selectedId: id, filteredTimeline: () => filteredTimeline,
      currentSelectedId: () => selectedId, currentJumpDay: () => jumpDay, currentGen: () => jumpGen,
      tlLoading: () => tlLoading, oldestCursor: () => oldestCursor, timelineLength: () => timeline.length,
      selectPerson: async (pid, append) => { if (selectedId !== id || jumpDay !== key || jumpGen !== gen) return; return selectPerson(pid, append); },
      scrollToPos: (pos) => applyJumpScrollPos(pos, filteredTimeline, findQ, quotedOpen, key, findHitIndices, () => selectedId === id && jumpDay === key && jumpGen === gen, (n) => (tlIndex = n), () => list?.stopPin(), (p) => list?.pinDayAtTop(p)),
    }).then((scrolled) => { if (jumpGen === gen && !scrolled) dayPin = false; });
  }

  async function cachedPhoto(hash: string): Promise<string | null> {
    if (!hash) return null;
    if (threadPhotoCache.has(hash)) return threadPhotoCache.get(hash) ?? null;
    const url = await readThreadPhoto(hash);
    threadPhotoCache.set(hash, url);
    if (!url && !threadBroken.includes(hash)) threadBroken = [...threadBroken, hash];
    return url;
  }

  function noteBroken(hash: string) {
    if (!hash) return;
    threadPhotoCache.set(hash, null);
    if (!threadBroken.includes(hash)) threadBroken = [...threadBroken, hash];
  }

  function hashForTarget(target: ThreadTarget): string {
    const steps = threadImages(filteredTimeline);
    const at = threadIndex(steps, target);
    if (at >= 0) return steps[at].hash;
    for (const row of timeline) {
      if (row.message_id !== target.message_id) continue;
      for (const a of row.attachments ?? []) {
        if (a.id === target.attachment_id) return a.cas_hash || "";
      }
    }
    return "";
  }

  async function stepLoaded(dir: 1 | -1, gen: number): Promise<boolean> {
    if (!threadTarget) return false;
    const target = { message_id: threadTarget.message_id, attachment_id: threadTarget.attachment_id };
    const steps = threadImages(filteredTimeline);
    const at = threadIndex(steps, target);
    if (at < 0) return false;
    const ordered = dir < 0 ? steps.slice(0, at).reverse() : steps.slice(at + 1);
    for (const step of ordered) {
      if (gen !== threadWalkGen || selectedId == null || !threadTarget) return false;
      const url = await cachedPhoto(step.hash);
      if (gen !== threadWalkGen || selectedId == null || !threadTarget) return false;
      if (!url) continue;
      threadSrc = url;
      threadTarget = { message_id: step.message_id, attachment_id: step.attachment_id };
      return true;
    }
    return false;
  }

  function closeThread() {
    threadTarget = null;
    threadSrc = null;
    invalidateThreadWalk();
  }

  async function openThreadImage(messageId: number, attachment: Attachment) {
    const gen = ++threadWalkGen;
    const token = ++threadPrevToken;
    threadPrevBusy = true;
    try {
      const hash = attachment.cas_hash ?? "";
      if (!hash) return;
      const url = await cachedPhoto(hash);
      if (gen !== threadWalkGen || selectedId == null) return;
      if (url) {
        threadSrc = url;
        threadTarget = { message_id: messageId, attachment_id: attachment.id };
        return;
      }
      const steps = threadImages(filteredTimeline);
      const at = threadIndex(steps, { message_id: messageId, attachment_id: attachment.id });
      const newer = at < 0 ? [] : steps.slice(at + 1);
      const older = at <= 0 ? [] : steps.slice(0, at).reverse();
      for (const step of [...newer, ...older]) {
        const nextUrl = await cachedPhoto(step.hash);
        if (gen !== threadWalkGen || selectedId == null) return;
        if (!nextUrl) continue;
        threadSrc = nextUrl;
        threadTarget = { message_id: step.message_id, attachment_id: step.attachment_id };
        return;
      }
    } finally {
      if (threadPrevToken === token) threadPrevBusy = false;
    }
  }

  async function onThreadNext() {
    if (!threadTarget || nextAtEnd) return;
    const gen = ++threadWalkGen;
    await stepLoaded(1, gen);
  }

  async function applyOlderThreadRows(rows: TimelineRow[]) {
    if (tlLoading) return;
    const seen = new Set(timeline.map((row) => row.message_id));
    const added = rows.filter((row) => !seen.has(row.message_id));
    if (added.length === 0) return;
    const apply = () => {
      timeline = added.concat(timeline);
      tlIndex += added.length;
      list?.resetHeights();
    };
    if (list) await list.holdAnchorAfterPrepend(added.length, apply);
    else apply();
  }

  async function onThreadPrev() {
    if (threadPrevBusy || !threadTarget || prevExhausted || selectedId == null) return;
    const token = ++threadPrevToken;
    threadPrevBusy = true;
    const gen = ++threadWalkGen;
    const person = selectedId;
    try {
      const moved = await stepLoaded(-1, gen);
      if (threadPrevToken !== token || gen !== threadWalkGen || selectedId !== person || !threadTarget) return;
      if (moved || threadAt < 0) return;
      if (!oldestCursor || threadOlderExhausted) {
        threadOlderExhausted = true;
        return;
      }
      const result = await collectOlderThreadRows({
        oldestCursor: () => oldestCursor,
        knownIds: () => timeline.map((row) => row.message_id),
        fetchPage: (before) =>
          api.personTimeline({
            id: person,
            includeGroups,
            limit: TIMELINE_PAGE_LIMIT,
            before,
            conversationId: selectedConversationId,
            ...(attachKindFilter !== "all" ? { attachKind: attachKindFilter } : {}),
          }),
        keeps: (row) =>
          (platformFilter === "all" || row.platform === platformFilter) &&
          (kindFilter === "all" || row.conversation_kind === kindFilter) &&
          (attachKindFilter === "all" || rowMatchesAttachKind(row, attachKindFilter)) &&
          (fromMeFilter === "all" ||
            (fromMeFilter === "me" && row.from_me === true) ||
            (fromMeFilter === "them" && row.from_me === false)),
        alive: () => threadWalkGen === gen && threadPrevToken === token && threadTarget != null && selectedId === person,
      });
      if (threadPrevToken !== token || gen !== threadWalkGen || selectedId !== person || !threadTarget) return;
      if (result.cancelled) return;
      if (result.rows.length > 0) await applyOlderThreadRows(result.rows);
      if (threadPrevToken !== token || gen !== threadWalkGen || selectedId !== person || !threadTarget) return;
      const landed = await stepLoaded(-1, gen);
      if (!landed && result.exhausted) threadOlderExhausted = true;
    } finally {
      if (threadPrevToken === token) threadPrevBusy = false;
    }
  }

  async function onThreadBroken() {
    if (!threadTarget) return;
    const gen = ++threadWalkGen;
    const hash = hashForTarget(threadTarget);
    noteBroken(hash);
    const moved = await stepLoaded(1, gen);
    if (gen !== threadWalkGen || !threadTarget) return;
    if (moved) return;
    const back = await stepLoaded(-1, gen);
    if (gen !== threadWalkGen) return;
    if (!back) closeThread();
  }

  export function closeCopyMenu() { list?.closeCopy(); }
  export function scrollToLatest() { list?.scrollToLatest(); }
  export function copySelected() { list?.copySelected(); }
  export function openGallery() { galleryOpen = true; }
</script>

<div class="flex min-h-0 min-w-0 flex-1 overflow-hidden flex-col">
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
        bind:attachKindFilter
        bind:fromMeFilter
        onAttachKindChange={() => {
          if (!selectedId) return;
          const keepConversation = true;
          void selectPerson(selectedId, false, keepConversation);
        }}
      />
      <div class="mb-3 flex items-center gap-2">
        <Input id="tl-find" data-tl-find type="search" bind:value={findQ} placeholder={t("findInThread")} aria-label={t("findInThread")} autocomplete="off" class="h-8 min-w-0 flex-1" oninput={() => (dayPin = false, jumpGen++)} onkeydown={onPaneFindKey} />
        <Input type={"date"} bind:value={jumpDay} aria-label={t("jumpToDay")} class="h-8 w-auto shrink-0" onchange={goToJumpDay} />
        {#if findQ}
          <span data-tl-hit-count class="shrink-0 text-xs tabular-nums text-muted-foreground">{findCount(filteredTimeline, findQ, tlIndex, quotedOpen)}</span>
        {/if}
        {#if lastReadMessageId}
          <Button type="button" variant="outline" size="sm" onclick={() => void goToLastRead()}>{t("lastTime")}</Button>
        {/if}
        <Button type="button" variant="outline" size="sm" data-person-gallery-open onclick={() => (galleryOpen = true)}>{t("media")}</Button>
      </div>
    {/if}
  </div>
  <div data-voice-note data-voice-host class="hidden" hidden>
    <audio bind:this={voiceHostEl} hidden preload="metadata" onended={onVoiceHostEnded}></audio>
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
    {attachKindFilter}
    {fromMeFilter}
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
      attachKindFilter = "all";
      fromMeFilter = "all";
      if (!selectedId) return;
      const keepConversation = true;
      void selectPerson(selectedId, false, keepConversation);
    }}
    onIncludeGroups={() => {
      if (!selectedId) return;
      includeGroups = true;
      writeIncludeGroupsPref(true);
      void selectPerson(selectedId);
      loadActivityYears(true);
    }}
    {openUrl}
    {showToast}
    {onSearchFromBubble}
    {onSearchThisConversation}
    {conversationLabel}
    {onCopyFail}
    {findQ}
    {lastReadMessageId}
    {persistLastRead}
    bind:selectedIds
    {liveSelectedIds}
    bind:anchorId
    {extendSelection}
    onClearDayPin={() => (dayPin = false, jumpGen++)}
    onOpenImage={(messageId, attachment) => void openThreadImage(messageId, attachment)}
  />
  {#if threadTarget && threadSrc}
    <TimelineLightbox
      src={threadSrc}
      alt={threadAlt}
      {nextAtEnd}
      {prevExhausted}
      onClose={closeThread}
      onPrev={() => void onThreadPrev()}
      onNext={() => void onThreadNext()}
      onBroken={() => void onThreadBroken()}
    />
  {/if}
  <PersonMediaDialog
    bind:open={galleryOpen}
    {selectedId}
    bind:includeGroups
    onIncludeGroups={() => {
      if (!selectedId) return;
      includeGroups = true;
      writeIncludeGroupsPref(true);
      void selectPerson(selectedId);
      loadActivityYears(true);
    }}
    {onImport}
    {openPersonAtMessage}
  />
  <p class="shrink-0 bg-background px-4 pb-4 pt-2 text-xs text-muted-foreground">
    Bodies are text only. Day headings follow the Mac timezone. <kbd class="rounded border border-border px-1">j</kbd>/<kbd
      class="rounded border border-border px-1">k</kbd
    >
    move.
    <kbd class="rounded border border-border px-1">/</kbd> filters people.
  </p>
</div>
