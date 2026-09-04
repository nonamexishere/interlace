<script lang="ts">
  import { tick } from "svelte";
  import type { TimelineRow } from "./api";
  import { localDay, localDayLabel } from "./formatTime";
  import { cancelDayHeadingPin, dayHeadingOffset, scrollDayHeadingToTop } from "./jumpDay";
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import TimelineRows from "./TimelineRows.svelte";
  import TimelineCopyMenu from "./TimelineCopyMenu.svelte";
  import TimelineEmpty from "./TimelineEmpty.svelte";
  import TimelineLatest from "./TimelineLatest.svelte";
  import { t } from "$lib/i18n";
  import { displayBody, isGroupedFollower as groupedFollower } from "./TimelineMail";
  import {
    ESTIMATED_ROW_HEIGHT,
    VIRTUALIZE_AFTER,
    computeVisibleRange,
    heightOf as heightAt,
    measureTimelineChrome,
    offsetOf as offsetAt,
    rowOffsetInPane, scrollAdjForHeightChanges, capturePrependAnchor, prependPinScrollTop,
  } from "./TimelineVirtual";

  let {
    timeline,
    filteredTimeline,
    selectedId,
    tlIndex = $bindable(0),
    tlLoading,
    tlAppending,
    tlError,
    includeGroups = $bindable(false),
    oldestCursor,
    density,
    onRetry,
    onPrepend,
    onImport,
    onShowAll,
    onIncludeGroups,
    openUrl,
    showToast,
    onSearchFromBubble,
    onCopyFail,
    findQ = "",
    quotedOpen = $bindable<Record<number, boolean>>({}),
    onClearDayPin,
  }: {
    timeline: TimelineRow[];
    filteredTimeline: { row: TimelineRow; index: number }[];
    selectedId: number | null;
    tlIndex?: number;
    tlLoading: boolean;
    tlAppending: boolean;
    tlError: string;
    includeGroups?: boolean;
    oldestCursor: string | null;
    density: string;
    onRetry: () => void;
    onPrepend: () => void;
    onImport: () => void;
    onShowAll: () => void;
    onIncludeGroups: () => void;
    openUrl: (url: string) => void;
    showToast: (message: string) => void;
    onSearchFromBubble: () => void;
    onCopyFail: () => void;
    findQ?: string;
    quotedOpen?: Record<number, boolean>;
    onClearDayPin?: () => void;
  } = $props();

  let tlScrollTop = $state(0);
  let tlViewportHeight = $state(480);
  let tlScrollHeight = $state(0);
  let tlChromeHeight = $state(0);
  let rowHeights = $state<Record<number, number>>({});
  let userScrolling = false;
  let userScrollUntil: ReturnType<typeof setTimeout> | null = null;
  let programmaticScroll = false;
  let pointerOnTimeline = false;
  let pinLatestObs: ResizeObserver | null = null;
  let pinLatestUntil: ReturnType<typeof setTimeout> | null = null;
  let prependN = $state(0), prependIdx = -1, prependViewOff = 0;
  let copyMenu = $state<{ x: number; y: number; text: string } | null>(null);
  const showLatest = $derived((() => { void tlScrollTop; void tlViewportHeight; void tlScrollHeight; const sc = document.getElementById("person-timeline"); return !!(sc && sc.scrollTop + sc.clientHeight < sc.scrollHeight - 4); })());

  $effect(() => {
    void density; void selectedId;
    clearPendingMeasures(); rowHeights = {}; quotedOpen = {};
  });

  function markUserScrolling() {
    userScrolling = true;
    if (userScrollUntil != null) clearTimeout(userScrollUntil);
    userScrollUntil = setTimeout(() => {
      userScrolling = false;
      userScrollUntil = null;
    }, 150);
  }

  function writeScrollTop(sc: HTMLElement, top: number) {
    programmaticScroll = true;
    sc.scrollTop = top;
    tlScrollTop = sc.scrollTop; tlViewportHeight = sc.clientHeight || tlViewportHeight; tlScrollHeight = sc.scrollHeight;
    programmaticScroll = false;
  }

  function heightOf(orig: number): number {
    return heightAt(rowHeights, orig);
  }

  function offsetOf(filteredPos: number): number {
    return offsetAt(filteredTimeline, rowHeights, filteredPos);
  }

  function onTimelineScroll(e: Event) {
    const el = e.currentTarget as HTMLElement | null;
    if (!el) return;
    tlScrollTop = el.scrollTop; tlViewportHeight = el.clientHeight || tlViewportHeight; tlScrollHeight = el.scrollHeight;
    if (programmaticScroll) return;
    cancelDayHeadingPin(); onClearDayPin?.();
    if (!pointerOnTimeline) return;
    markUserScrolling();
    if (pinLatestObs && el.scrollTop + el.clientHeight < el.scrollHeight - 4) {
      stopPinLatest();
    }
  }

  function onTimelineWheel() {
    cancelDayHeadingPin(); stopPinLatest(); markUserScrolling(); onClearDayPin?.();
  }

  function onTimelinePointerDown() { pointerOnTimeline = true; }
  function onTimelinePointerUp() { pointerOnTimeline = false; }

  const visibleRange = $derived(
    computeVisibleRange(filteredTimeline.length, tlViewportHeight, tlScrollTop + prependN * ESTIMATED_ROW_HEIGHT, (i) =>
      heightOf(filteredTimeline[i].index),
    ),
  );

  const spacerTop = $derived(offsetOf(visibleRange.startIndex));
  const spacerBottom = $derived(
    Math.max(0, offsetOf(filteredTimeline.length) - offsetOf(visibleRange.endIndex)),
  );

  const windowedDayGroups = $derived.by(() => {
    const startIndex = visibleRange.startIndex;
    const endIndex = visibleRange.endIndex;
    const rows = filteredTimeline.slice(startIndex, endIndex);
    const groups: { key: string; label: string; rows: { row: TimelineRow; index: number }[] }[] =
      [];
    for (let i = 0; i < rows.length; i++) {
      const { row, index } = rows[i];
      const key = localDay(row.sent_at, row.platform);
      const dayChanged =
        i === 0 ||
        key !== localDay(rows[i - 1]?.row.sent_at, rows[i - 1]?.row.platform);
      const last = groups[groups.length - 1];
      if (!last || dayChanged) {
        groups.push({
          key,
          label: key ? localDayLabel(row.sent_at, row.platform) : "",
          rows: [{ row, index }],
        });
      } else {
        last.rows.push({ row, index });
      }
    }
    return groups;
  });

  export function ensureTlIndexVisible(index: number) {
    const pos = filteredTimeline.findIndex((item) => item.index === index);
    if (pos < 0) return;
    const sc = document.getElementById("person-timeline");
    if (!sc) return;
    const mounted = sc.querySelector(`[data-tl-index="${index}"]`);
    const rowTop =
      mounted instanceof HTMLElement
        ? rowOffsetInPane(sc, mounted)
        : tlChromeHeight + offsetOf(pos);
    const rowH =
      mounted instanceof HTMLElement
        ? mounted.getBoundingClientRect().height
        : heightOf(filteredTimeline[pos]?.index ?? index);
    const rowBottom = rowTop + rowH;
    const viewTop = sc.scrollTop;
    const viewBottom = viewTop + sc.clientHeight;
    if (rowTop < viewTop) {
      writeScrollTop(sc, Math.max(0, rowTop - ESTIMATED_ROW_HEIGHT));
    } else if (rowBottom > viewBottom) {
      writeScrollTop(sc, rowBottom - sc.clientHeight + ESTIMATED_ROW_HEIGHT);
    }
  }

  let pendingMeasures: Record<number, number> = {};
  let pendingChrome = false;
  let measureRaf = 0;
  let measureEpoch = 0;

  function scheduleMeasureFlush() {
    if (measureRaf) return;
    measureRaf = requestAnimationFrame(flushRowMeasures);
  }

  function clearPendingMeasures() {
    pendingMeasures = {}; measureEpoch++;
    if (measureRaf) { cancelAnimationFrame(measureRaf); measureRaf = 0; }
  }

  function scheduleChromeMeasure() {
    pendingChrome = true;
    scheduleMeasureFlush();
  }

  function applyRowMeasure(orig: number, h: number) {
    if (!(h > 0) || !Number.isFinite(h)) return;
    if ((pendingMeasures[orig] ?? rowHeights[orig]) === h) return;
    pendingMeasures[orig] = h;
    scheduleMeasureFlush();
  }

  function flushRowMeasures() {
    measureRaf = 0;
    const sc = document.getElementById("person-timeline");
    if (pendingChrome) {
      pendingChrome = false;
      if (sc) {
        const chrome = measureTimelineChrome(sc);
        if (chrome !== tlChromeHeight) tlChromeHeight = chrome;
      }
    }
    const pending = pendingMeasures;
    pendingMeasures = {};
    const listScroll = Math.max(0, (sc?.scrollTop ?? tlScrollTop) - tlChromeHeight);
    const windowed = filteredTimeline.length > VIRTUALIZE_AFTER;
    const { next, adj, changed } = scrollAdjForHeightChanges(
      filteredTimeline, rowHeights, pending, listScroll,
    );
    if (changed) rowHeights = next;
    const epoch = measureEpoch;
    if (windowed && adj !== 0 && sc && !pinLatestObs) void tick().then(() => { if (epoch !== measureEpoch || pinLatestObs) return; writeScrollTop(sc, sc.scrollTop + adj); });
  }

  function measureTlRow(node: HTMLElement, orig: number) {
    const read = () => {
      const raw = node.getAttribute("data-tl-index");
      const idx = raw != null ? Number(raw) : orig;
      if (!Number.isFinite(idx)) return;
      const h = Math.round(node.getBoundingClientRect().height);
      applyRowMeasure(idx, h);
      scheduleChromeMeasure();
    };
    const obs = new ResizeObserver(read);
    obs.observe(node);
    read();
    return {
      update(nextOrig: number) {
        orig = nextOrig;
        read();
      },
      destroy() {
        obs.disconnect();
      },
    };
  }

  $effect(() => {
    void selectedId;
    void timeline.length;
    void filteredTimeline.length;
    scheduleChromeMeasure();
    void tick().then(() => { const sc = document.getElementById("person-timeline"); if (sc) { tlScrollTop = sc.scrollTop; tlViewportHeight = sc.clientHeight || tlViewportHeight; tlScrollHeight = sc.scrollHeight; } });
  });

  function stopPinLatest() {
    pinLatestObs?.disconnect();
    pinLatestObs = null;
    if (pinLatestUntil != null) {
      clearTimeout(pinLatestUntil);
      pinLatestUntil = null;
    }
  }

  function pinTimelineLatest(sc: HTMLElement) {
    writeScrollTop(sc, sc.scrollHeight);
  }

  function syncOpenPersonScroll(sc: HTMLElement) {
    tlViewportHeight = sc.clientHeight || tlViewportHeight;
    const keep = tlScrollTop;
    pinTimelineLatest(sc);
    if (sc.scrollTop + sc.clientHeight < sc.scrollHeight - 4) {
      pinTimelineLatest(sc);
    }
    if (sc.scrollTop <= 4 && keep > (sc.clientHeight || 0)) {
      tlScrollTop = keep;
      return;
    }
    if (sc.scrollTop !== tlScrollTop) tlScrollTop = sc.scrollTop;
  }

  function watchPinLatest(sc: HTMLElement) {
    stopPinLatest();
    syncOpenPersonScroll(sc);
    const ol = sc.querySelector("ol");
    pinLatestObs = new ResizeObserver(() => {
      tlViewportHeight = sc.clientHeight || tlViewportHeight;
      const keep = tlScrollTop;
      writeScrollTop(sc, sc.scrollHeight);
      if (sc.scrollTop <= 4 && keep > (sc.clientHeight || 0)) {
        tlScrollTop = keep;
      }
    });
    pinLatestObs.observe(sc);
    if (ol) pinLatestObs.observe(ol);
    pinLatestUntil = setTimeout(stopPinLatest, 600);
  }

  export function applyOpenPersonWindow(gen: number, currentGen: () => number) {
    const sc0 = document.getElementById("person-timeline");
    if (sc0) tlViewportHeight = sc0.clientHeight || tlViewportHeight;
    const estTotal = Math.max(offsetOf(filteredTimeline.length), ESTIMATED_ROW_HEIGHT);
    tlScrollTop = estTotal;
    void tick().then(() => {
      if (gen !== currentGen()) return;
      const sc = document.getElementById("person-timeline");
      if (!sc) return;
      tlViewportHeight = sc.clientHeight || tlViewportHeight;
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (gen !== currentGen()) return;
          tlViewportHeight = sc.clientHeight || tlViewportHeight;
          const keep = tlScrollTop;
          programmaticScroll = true;
          sc.scrollTop = sc.scrollHeight;
          tlScrollTop = sc.scrollTop;
          programmaticScroll = false;
          if (sc.scrollTop <= 4 && keep > (sc.clientHeight || 0)) {
            tlScrollTop = keep;
          } else if (sc.scrollTop !== tlScrollTop) {
            tlScrollTop = sc.scrollTop;
          }
          watchPinLatest(sc);
        });
      });
    });
  }

  export function shiftHeightsForPrepend(n: number) {
    const next: Record<number, number> = {};
    for (const [k, v] of Object.entries(rowHeights)) {
      next[Number(k) + n] = v;
    }
    const a = capturePrependAnchor(document.getElementById("person-timeline"), tlIndex);
    prependN = n; prependIdx = a ? a.index + n : -1; prependViewOff = a ? a.viewOffset : 0;
    clearPendingMeasures();
    rowHeights = next;
  }

  export function resetHeights() {
    clearPendingMeasures();
    rowHeights = {};
  }

  export function preserveScrollAfterPrepend(prevHeight: number) {
    const sc = document.getElementById("person-timeline");
    const idx = prependIdx >= 0 ? prependIdx : tlIndex, off = prependViewOff;
    prependN = 0; prependIdx = -1; prependViewOff = 0;
    if (sc) writeScrollTop(sc, prependPinScrollTop(sc, idx, off, prevHeight));
  }

  export function stopPin() { stopPinLatest(); cancelDayHeadingPin(); }

  export function estimateScrollToIndex(index: number) {
    const hitPos = filteredTimeline.findIndex((item) => item.index === index);
    const estTop = Math.max(
      0,
      offsetOf(hitPos >= 0 ? hitPos : index) - ESTIMATED_ROW_HEIGHT * 2,
    );
    tlScrollTop = estTop;
  }

  export function pinDayAtTop(filteredPos: number) {
    const item = filteredTimeline[filteredPos];
    if (!item) return;
    const estimateTop = Math.max(0, tlChromeHeight + offsetOf(filteredPos) + dayHeadingOffset(filteredTimeline, filteredPos));
    tlScrollTop = estimateTop; scrollDayHeadingToTop(item.index, estimateTop, writeScrollTop);
  }

  function isGroupedFollower(i: number): boolean {
    return groupedFollower(filteredTimeline, i, localDay);
  }

  function toggleQuoted(messageId: number, e: Event) {
    e.stopPropagation(); e.preventDefault();
    quotedOpen = { ...quotedOpen, [messageId]: !quotedOpen[messageId] };
  }

  function openCopyMenu(e: MouseEvent, row: TimelineRow) {
    e.preventDefault();
    copyMenu = { x: e.clientX, y: e.clientY, text: row.body_text || row.subject || "" };
  }

  function closeCopyMenu() { copyMenu = null; }

  export function scrollToLatest() {
    const sc = document.getElementById("person-timeline");
    if (!sc) return;
    cancelDayHeadingPin(); onClearDayPin?.();
    watchPinLatest(sc);
  }

  async function copyText() {
    if (!copyMenu) return;
    const text = displayBody(copyMenu.text);
    copyMenu = null;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      onCopyFail();
    }
  }

  function searchFromBubble() { closeCopyMenu(); onSearchFromBubble(); }

  function onCopyMenuAway(e: MouseEvent) {
    if (!copyMenu) return;
    const el = e.target as HTMLElement | null;
    if (el?.closest("[data-copy-menu]")) return;
    closeCopyMenu();
  }

  $effect(() => {
    const sync = () => { const sc = document.getElementById("person-timeline"); if (sc) { tlScrollTop = sc.scrollTop; tlViewportHeight = sc.clientHeight || tlViewportHeight; tlScrollHeight = sc.scrollHeight; } };
    window.addEventListener("mousedown", onCopyMenuAway);
    window.addEventListener("pointerup", onTimelinePointerUp);
    window.addEventListener("resize", sync);
    return () => { window.removeEventListener("mousedown", onCopyMenuAway); window.removeEventListener("pointerup", onTimelinePointerUp); window.removeEventListener("resize", sync); stopPinLatest(); };
  });

  export function closeCopy() { closeCopyMenu(); }
  export function copySelected() {
    const row = tlIndex < 0 ? null : filteredTimeline.find((item) => item.index === tlIndex)?.row ?? timeline[tlIndex];
    if (!row) return;
    navigator.clipboard.writeText(displayBody(row.body_text || row.subject || "")).catch(() => onCopyFail());
  }
</script>

<div class="relative min-h-0 flex-1 flex min-w-0 flex-col">
<ScrollArea
  id="person-timeline"
  class="min-h-0 min-w-0 flex-1 px-4 pb-8{filteredTimeline.length > VIRTUALIZE_AFTER ? ' tl-windowed' : ''}"
  aria-busy={tlLoading}
  onscroll={onTimelineScroll}
  onwheel={onTimelineWheel}
  onpointerdown={onTimelinePointerDown}
>
  <TimelineEmpty
    {tlLoading}
    {tlAppending}
    {selectedId}
    {tlError}
    {timeline}
    {filteredTimeline}
    {includeGroups}
    {onRetry}
    {onShowAll}
    {onIncludeGroups}
    {onImport}
  />
  <TimelineRows
    {windowedDayGroups}
    {spacerTop}
    {spacerBottom}
    {tlIndex}
    {quotedOpen}
    {measureTlRow}
    {isGroupedFollower}
    onSelectIndex={(index) => (tlIndex = index)}
    onContextMenu={openCopyMenu}
    {toggleQuoted}
    {openUrl}
    {showToast}
    showLoadOlder={!!(timeline.length && oldestCursor && filteredTimeline.length > 0)}
    {tlLoading}
    {onPrepend}
    {findQ}
  />
  <div id="timeline-end"></div>
</ScrollArea>
{#if showLatest || tlAppending}
  <TimelineLatest onclick={scrollToLatest}>{t("latest")}</TimelineLatest>
{/if}
{#if copyMenu}
  <TimelineCopyMenu x={copyMenu.x} y={copyMenu.y} onCopy={copyText} onSearch={searchFromBubble} />
{/if}
</div>
