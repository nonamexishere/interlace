import { tick } from "svelte";
import { localDay } from "./formatTime";

export type JumpDayRow = {
  sent_at?: string | null;
  platform?: string | null;
};

export type JumpDayItem = { row: JumpDayRow; index: number };

export type JumpDayCtx = {
  key: string;
  filteredTimeline: () => JumpDayItem[];
  selectedId: number | null;
  tlLoading: () => boolean;
  oldestCursor: () => string | null;
  timelineLength: () => number;
  selectPerson: (id: number, append: true) => Promise<unknown>;
  scrollToPos: (filteredPos: number) => void;
};

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

/** Pin that day's first .day-heading to the top of #person-timeline. */
export function scrollDayHeadingToTop(
  origIndex: number,
  estimateTop: number,
  writeScrollTop: (sc: HTMLElement, top: number) => void,
): void {
  const sc = document.getElementById("person-timeline");
  if (!sc) return;
  writeScrollTop(sc, Math.max(0, estimateTop));
  void tick().then(() => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
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
 * Already loaded → scroll. Older → selectPerson(..., true) prepend
 * until the heading exists or the page is empty/short.
 */
export async function jumpToLocalDay(ctx: JumpDayCtx): Promise<void> {
  const key = (ctx.key ?? "").trim();
  if (!key) return;
  const hit = () => firstLocalDayIndex(ctx.filteredTimeline(), key);
  let pos = hit();
  if (pos >= 0) {
    ctx.scrollToPos(pos);
    return;
  }
  const id = ctx.selectedId;
  if (!id) return;
  const limit = 80;
  while (true) {
    while (ctx.tlLoading()) await tick();
    if (!ctx.oldestCursor()) break;
    const beforeLen = ctx.timelineLength();
    await ctx.selectPerson(id, true);
    const page = { length: ctx.timelineLength() - beforeLen };
    pos = hit();
    if (pos >= 0) {
      ctx.scrollToPos(pos);
      return;
    }
    if (page.length === 0 || page.length < limit) break;
  }
}
