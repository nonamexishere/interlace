import { tick } from "svelte";
import { localDay } from "./formatTime";

export type JumpDayRow = {
  sent_at?: string | null;
  platform?: string | null;
};

export type JumpDayItem = { row: JumpDayRow; index: number };

export type JumpDayCtx = {
  key: string;
  gen: number;
  selectedId: number | null;
  currentSelectedId: () => number | null;
  currentJumpDay: () => string;
  currentGen: () => number;
  filteredTimeline: () => JumpDayItem[];
  tlLoading: () => boolean;
  oldestCursor: () => string | null;
  timelineLength: () => number;
  selectPerson: (id: number, append: true) => Promise<unknown>;
  scrollToPos: (filteredPos: number) => void;
};

/** True when selectedId / jumpDay / jumpGen no longer match the captured jump. */
export function jumpStale(ctx: JumpDayCtx): boolean {
  return (
    ctx.currentSelectedId() !== ctx.selectedId ||
    ctx.key !== ctx.currentJumpDay() ||
    ctx.currentGen() !== ctx.gen
  );
}

/**
 * tlIndex after a day pin. Empty Find → that day's first row.
 * Find on: only the day's first row if it is already a hit, or a hit
 * on that local day. No hit on that day → null (leave tlIndex).
 */
export function dayPinTlIndex(
  item: JumpDayItem | undefined,
  hits: number[],
  filteredTimeline: JumpDayItem[],
  key: string,
  findQ: string,
): number | null {
  if (!item) return null;
  if (!(findQ ?? "").trim()) return item.index;
  if (hits.includes(item.index)) return item.index;
  for (const h of hits) {
    const hit = filteredTimeline.find((it) => it.index === h);
    if (!hit) continue;
    if (localDay(hit.row.sent_at, hit.row.platform) === key) return h;
  }
  return null;
}

/** Closest visible timeline index (same rule as the chip-filter snap). */
export function nearestVisibleTlIndex(from: number, visible: number[]): number {
  if (!visible.length) return from;
  let best = visible[0];
  let bestDist = Math.abs(visible[0] - from);
  for (let i = 1; i < visible.length; i++) {
    const idx = visible[i];
    const d = Math.abs(idx - from);
    if (d < bestDist || (d === bestDist && idx > best)) {
      best = idx;
      bestDist = d;
    }
  }
  return best;
}

/** First filteredTimeline row whose host-calendar localDay matches key. */
export function firstLocalDayIndex(
  filteredTimeline: JumpDayItem[],
  key: string,
): number {
  if (!key) return -1;
  for (let i = 0; i < filteredTimeline.length; i++) {
    const { sent_at, platform } = filteredTimeline[i].row;
    const day = localDay(sent_at, platform);
    if (day === "") continue;
    if (day === key) return i;
  }
  return -1;
}

/** Max prepend pages a day jump may request before a quiet miss. */
export const JUMP_DAY_PAGE_CAP = 80;

/** Page size for personTimeline loads and jump short-page checks. */
export const TIMELINE_PAGE_LIMIT = 80;

/** Apply day-jump scroll: tlIndex pin + stopPin + pinDayAtTop (no-op if !alive). */
export function applyJumpScrollPos(
  pos: number,
  filteredTimeline: JumpDayItem[],
  findQ: string,
  quotedOpen: Record<number, boolean> | undefined,
  key: string,
  findHitIndices: (
    tl: JumpDayItem[],
    q: string,
    quoted: Record<number, boolean> | undefined,
  ) => number[],
  alive: () => boolean,
  setTlIndex: (n: number) => void,
  stopPin: () => void,
  pinDayAtTop: (pos: number) => void,
): void {
  if (!alive()) return;
  const item = filteredTimeline[pos];
  const next = dayPinTlIndex(
    item,
    findHitIndices(filteredTimeline, findQ, quotedOpen),
    filteredTimeline,
    key,
    findQ,
  );
  if (next != null) setTlIndex(next);
  stopPin();
  pinDayAtTop(pos);
}

/** Min/max host-calendar localDay over dated filtered rows. */
export function loadedDayRange(
  items: JumpDayItem[],
): { oldest: string; newest: string } | null {
  let oldest = "";
  let newest = "";
  for (const it of items) {
    const day = localDay(it.row.sent_at, it.row.platform);
    if (day === "") continue;
    if (!oldest || day < oldest) oldest = day;
    if (!newest || day > newest) newest = day;
  }
  if (!oldest) return null;
  return { oldest, newest };
}

/**
 * Prepend earlier pages only when the target is older than the loaded window.
 * No dated rows → true (first page can be undated). Newer / in-range → false.
 */
export function shouldLoadOlderForJump(
  key: string,
  range: { oldest: string; newest: string } | null,
): boolean {
  if (!range) return true;
  return key < range.oldest;
}

let dayPinToken = 0;
export function cancelDayHeadingPin(): void {
  dayPinToken++;
}

/** Pin that day's first .day-heading to the top of #person-timeline. */
export function scrollDayHeadingToTop(
  origIndex: number,
  estimateTop: number,
  writeScrollTop: (sc: HTMLElement, top: number) => void,
): void {
  const sc = document.getElementById("person-timeline");
  if (!sc) return;
  const token = ++dayPinToken;
  writeScrollTop(sc, Math.max(0, estimateTop));
  void tick().then(() => {
    if (token !== dayPinToken) return;
    requestAnimationFrame(() => {
      if (token !== dayPinToken) return;
      requestAnimationFrame(() => {
        if (token !== dayPinToken) return;
        const row = sc.querySelector(`[data-tl-index="${origIndex}"]`);
        const heading =
          row instanceof Element
            ? row.closest(".day-group")?.querySelector(".day-heading")
            : null;
        if (!(heading instanceof HTMLElement)) return;
        const top =
          heading.getBoundingClientRect().top -
          sc.getBoundingClientRect().top +
          sc.scrollTop;
        writeScrollTop(sc, Math.max(0, top));
      });
    });
  });
}

/**
 * Jump to the first sticky day heading for YYYY-MM-DD.
 * Already loaded → scroll. Older than loaded window → selectPerson(..., true)
 * prepend until the heading exists, empty/short page, range gap, or page cap.
 * Newer day or in-range gap → quiet miss (no prepend walk).
 * @returns true if scrollToPos ran; false on quiet miss / stale / empty / cap.
 */
export async function jumpToLocalDay(ctx: JumpDayCtx): Promise<boolean> {
  const key = (ctx.key ?? "").trim();
  if (!key) return false;
  if (jumpStale(ctx)) return false;
  const hit = () => firstLocalDayIndex(ctx.filteredTimeline(), key);
  let pos = hit();
  if (pos >= 0) {
    if (jumpStale(ctx)) return false;
    ctx.scrollToPos(pos);
    return true;
  }
  const id = ctx.selectedId;
  if (!id) return false;
  let range = loadedDayRange(ctx.filteredTimeline());
  if (!shouldLoadOlderForJump(key, range)) return false;
  let pages = 0;
  while (pages < JUMP_DAY_PAGE_CAP) {
    while (ctx.tlLoading()) await tick();
    if (jumpStale(ctx)) return false;
    if (!ctx.oldestCursor()) break;
    range = loadedDayRange(ctx.filteredTimeline());
    if (!shouldLoadOlderForJump(key, range)) return false;
    const beforeLen = ctx.timelineLength();
    if (jumpStale(ctx)) return false;
    await ctx.selectPerson(id, true);
    await tick();
    if (jumpStale(ctx)) return false;
    const page = { length: ctx.timelineLength() - beforeLen };
    pos = hit();
    if (pos >= 0) {
      if (jumpStale(ctx)) return false;
      ctx.scrollToPos(pos);
      return true;
    }
    if (page.length === 0 || page.length < TIMELINE_PAGE_LIMIT) break;
    pages++;
  }
  return false;
}
