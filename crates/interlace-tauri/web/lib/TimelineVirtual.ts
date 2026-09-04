export const ESTIMATED_ROW_HEIGHT = 88;
export const OVERSCAN = 15;
export const VIRTUALIZE_AFTER = 250;

export function heightOf(rowHeights: Record<number, number>, orig: number): number {
  return rowHeights[orig] ?? ESTIMATED_ROW_HEIGHT;
}

export function offsetOf(
  filteredTimeline: { index: number }[],
  rowHeights: Record<number, number>,
  filteredPos: number,
): number {
  const n = Math.max(0, Math.min(filteredPos, filteredTimeline.length));
  let sum = 0;
  for (let k = 0; k < n; k++) {
    sum += heightOf(rowHeights, filteredTimeline[k].index);
  }
  return sum;
}

export function computeVisibleRange(
  total: number,
  tlViewportHeight: number,
  tlScrollTop: number,
  heightAt: (i: number) => number,
): { startIndex: number; endIndex: number } {
  if (total === 0) return { startIndex: 0, endIndex: 0 };
  if (total <= VIRTUALIZE_AFTER) return { startIndex: 0, endIndex: total };
  const vh = Math.max(tlViewportHeight, 200);
  const scrollTop = Math.max(0, tlScrollTop);
  let startIndex = 0;
  let acc = 0;
  while (startIndex < total) {
    const h = heightAt(startIndex);
    if (acc + h > scrollTop) break;
    acc += h;
    startIndex += 1;
  }
  let endIndex = startIndex;
  let endAcc = acc;
  const viewBottom = scrollTop + vh;
  while (endIndex < total && endAcc < viewBottom) {
    endAcc += heightAt(endIndex);
    endIndex += 1;
  }
  startIndex = Math.max(0, startIndex - OVERSCAN);
  endIndex = Math.min(total, endIndex + OVERSCAN);
  if (startIndex >= total) {
    const windowRows = Math.ceil(vh / ESTIMATED_ROW_HEIGHT) + OVERSCAN * 2;
    startIndex = Math.max(0, total - windowRows);
    endIndex = total;
  } else if (endIndex <= startIndex) {
    endIndex = Math.min(total, startIndex + 1);
  }
  return { startIndex, endIndex };
}

export function rowOffsetInPane(sc: HTMLElement, el: HTMLElement): number {
  return el.getBoundingClientRect().top - sc.getBoundingClientRect().top + sc.scrollTop;
}

export function measureOuterHeight(el: HTMLElement): number {
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  return Math.round(
    r.height + (parseFloat(cs.marginTop) || 0) + (parseFloat(cs.marginBottom) || 0),
  );
}

export function measureTimelineChrome(sc: HTMLElement): number {
  let h = 0;
  const older = sc.querySelector("[data-load-older]");
  if (older instanceof HTMLElement) h += measureOuterHeight(older);
  const heading = sc.querySelector(".day-heading");
  if (heading instanceof HTMLElement) h += measureOuterHeight(heading);
  return h;
}

export type ScrollHeightAdj = {
  next: Record<number, number>;
  adj: number;
  changed: boolean;
};

export function scrollAdjForHeightChanges(
  filteredTimeline: { index: number }[],
  rowHeights: Record<number, number>,
  pending: Record<number, number>,
  listScroll: number,
): ScrollHeightAdj {
  const next: Record<number, number> = { ...rowHeights };
  let adj = 0;
  let changed = false;
  for (const key of Object.keys(pending)) {
    const orig = Number(key);
    const h = pending[orig];
    if (!(h > 0) || !Number.isFinite(h)) continue;
    if (rowHeights[orig] === h) continue;
    const prev = rowHeights[orig] ?? ESTIMATED_ROW_HEIGHT;
    const pos = filteredTimeline.findIndex((it) => it.index === orig);
    if (pos >= 0) {
      const oldTop = offsetOf(filteredTimeline, rowHeights, pos);
      if (oldTop < listScroll) adj += h - prev;
    }
    next[orig] = h;
    changed = true;
  }
  return { next, adj, changed };
}

export function capturePrependAnchor(
  sc: HTMLElement | null,
  tlIndex: number,
): { index: number; viewOffset: number } | null {
  if (!sc) return null;
  const hit =
    sc.querySelector(`[data-tl-index="${tlIndex}"]`) ?? sc.querySelector("[data-tl-index]");
  if (!(hit instanceof HTMLElement)) return null;
  const raw = hit.getAttribute("data-tl-index");
  const index = raw != null ? Number(raw) : tlIndex;
  if (!Number.isFinite(index)) return null;
  return { index, viewOffset: rowOffsetInPane(sc, hit) - sc.scrollTop };
}

export function prependPinScrollTop(
  sc: HTMLElement,
  index: number,
  viewOffset: number,
  prevHeight: number,
): number {
  const el = sc.querySelector(`[data-tl-index="${index}"]`);
  return el instanceof HTMLElement
    ? rowOffsetInPane(sc, el) - viewOffset
    : sc.scrollTop + (sc.scrollHeight - prevHeight);
}
