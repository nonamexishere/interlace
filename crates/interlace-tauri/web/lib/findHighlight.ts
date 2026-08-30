import { displayBody, isMailRow, splitQuotedBody } from "./TimelineMail";

/** Segment of an in-conversation find: plain text or a substring mark. */
export type FindSegment =
  | { kind: "text"; text: string }
  | { kind: "mark"; text: string };

type FindRow = {
  body_text?: string | null;
  subject?: string | null;
  platform?: string | null;
  conversation_kind?: string | null;
  message_id?: number;
};

/** Visible fields only — per-field includes, never a joined "subject body" phrase. */
function visibleFindFields(
  row: FindRow,
  quotedOpen: Record<number, boolean> = {},
): string[] {
  const subject = row.subject ?? "";
  if (!isMailRow(row)) {
    return [displayBody(row.body_text || subject)];
  }
  const parts = splitQuotedBody(row.body_text || "");
  const fields = [subject, displayBody(parts.main)];
  if (quotedOpen[row.message_id ?? 0]) fields.push(displayBody(parts.quoted));
  return fields;
}

/**
 * Split visible text on a client substring (case-insensitive).
 * Never returns HTML — callers render <mark> as Svelte text siblings.
 */
export function splitFind(text: string, findQ: string): FindSegment[] {
  const raw = text ?? "";
  const q = (findQ ?? "").trim();
  if (!raw) return [];
  if (!q) return [{ kind: "text", text: raw }];

  const lower = raw.toLowerCase();
  const needle = q.toLowerCase();
  const segments: FindSegment[] = [];
  let from = 0;
  while (from < raw.length) {
    const i = lower.indexOf(needle, from);
    if (i < 0) {
      segments.push({ kind: "text", text: raw.slice(from) });
      break;
    }
    if (i > from) segments.push({ kind: "text", text: raw.slice(from, i) });
    segments.push({ kind: "mark", text: raw.slice(i, i + needle.length) });
    from = i + needle.length;
  }
  return segments.length ? segments : [{ kind: "text", text: raw }];
}

export function rowMatchesFind(
  row: FindRow,
  findQ: string,
  quotedOpen: Record<number, boolean> = {},
): boolean {
  const q = (findQ ?? "").trim().toLowerCase();
  if (!q) return false;
  return visibleFindFields(row, quotedOpen).some((field) =>
    field.toLowerCase().includes(q),
  );
}

export function findHitIndices(
  filteredTimeline: { row: FindRow; index: number }[],
  findQ: string,
  quotedOpen: Record<number, boolean> = {},
): number[] {
  const q = (findQ ?? "").trim();
  if (!q) return [];
  const hits: number[] = [];
  for (const item of filteredTimeline) {
    if (rowMatchesFind(item.row, q, quotedOpen)) hits.push(item.index);
  }
  return hits;
}

export function stepFindIndex(
  filteredTimeline: { row: FindRow; index: number }[],
  findQ: string,
  tlIndex: number,
  dir: 1 | -1,
  quotedOpen: Record<number, boolean> = {},
): number | null {
  const hits = findHitIndices(filteredTimeline, findQ, quotedOpen);
  if (!hits.length) return null;
  const cur = hits.indexOf(tlIndex);
  if (cur < 0) return dir > 0 ? hits[0] : hits[hits.length - 1];
  return hits[(cur + dir + hits.length) % hits.length];
}

/** Quiet `current/total` (1-based). Empty query hides; zero hits is `0/0`. */
export function findCount(
  filteredTimeline: { row: FindRow; index: number }[],
  findQ: string,
  tlIndex: number,
  quotedOpen: Record<number, boolean> = {},
): string {
  const q = (findQ ?? "").trim();
  if (!q) return "";
  const hits = findHitIndices(filteredTimeline, findQ, quotedOpen);
  if (!hits.length) return "0/0";
  const i = hits.indexOf(tlIndex);
  const current = i < 0 ? 1 : i + 1;
  return `${current}/${hits.length}`;
}

/** Snap to hits[0] only when there are hits and tlIndex is not one of them. */
export function snapFindHit(hits: number[], tlIndex: number): number | null {
  if (!hits.length) return null;
  if (hits.includes(tlIndex)) return null;
  return hits[0];
}

export function onFindKey(
  e: KeyboardEvent,
  findQ: string,
  setFindQ: (q: string) => void,
  step: (dir: 1 | -1) => void,
): void {
  if (e.key === "Enter") {
    e.preventDefault();
    if (e.shiftKey) step(-1);
    else step(1);
    return;
  }
  if (e.key === "Escape") {
    e.preventDefault();
    e.stopPropagation();
    if (findQ) {
      setFindQ("");
      return;
    }
    (e.currentTarget as HTMLInputElement | null)?.blur();
  }
}
