/** Frozen contiguous message_id range at extend time (not tlIndex). */
export function rangeIds(
  filteredTimeline: { row: { message_id: number } }[],
  anchorId: number | null,
  targetId: number,
): Set<number> {
  const ids = filteredTimeline.map((item) => item.row.message_id);
  const b = ids.indexOf(targetId);
  if (b < 0) return new Set(anchorId != null ? [anchorId] : []);
  const a = anchorId != null ? ids.indexOf(anchorId) : b;
  const start = Math.min(a < 0 ? b : a, b);
  const end = Math.max(a < 0 ? b : a, b);
  return new Set(ids.slice(start, end + 1));
}

/** Leftover File → Open must not paint Ada's rings on Berk's archive. */
export function selectionLive(loadedArchiveId: string, archiveId: string): boolean {
  return loadedArchiveId === archiveId;
}
