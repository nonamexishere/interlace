import { displayBody, splitQuotedBody } from "./TimelineMail";

/** Segment of an in-conversation find: plain text or a substring mark. */
export type FindSegment =
  | { kind: "text"; text: string }
  | { kind: "mark"; text: string };

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

/** Visible haystack: displayBody(body_text) + subject. Not folded quoted. */
export function findHaystack(row: {
  body_text?: string | null;
  subject?: string | null;
}): string {
  const subject = row.subject ?? "";
  const parts = splitQuotedBody(row.body_text || "");
  return `${subject} ${displayBody(parts.main)}`;
}

export function rowMatchesFind(
  row: { body_text?: string | null; subject?: string | null },
  findQ: string,
): boolean {
  const q = (findQ ?? "").trim().toLowerCase();
  if (!q) return false;
  return findHaystack(row).toLowerCase().includes(q);
}

export function findHitIndices(
  filteredTimeline: {
    row: { body_text?: string | null; subject?: string | null };
    index: number;
  }[],
  findQ: string,
): number[] {
  const q = (findQ ?? "").trim();
  if (!q) return [];
  const hits: number[] = [];
  for (const item of filteredTimeline) {
    if (rowMatchesFind(item.row, q)) hits.push(item.index);
  }
  return hits;
}

export function stepFindIndex(
  filteredTimeline: {
    row: { body_text?: string | null; subject?: string | null };
    index: number;
  }[],
  findQ: string,
  tlIndex: number,
  dir: 1 | -1,
): number | null {
  const hits = findHitIndices(filteredTimeline, findQ);
  if (!hits.length) return null;
  const cur = hits.indexOf(tlIndex);
  if (cur < 0) return dir > 0 ? hits[0] : hits[hits.length - 1];
  return hits[(cur + dir + hits.length) % hits.length];
}

/** Quiet `current/total` (1-based). Empty query hides; zero hits is `0/0`. */
export function findCount(
  filteredTimeline: {
    row: { body_text?: string | null; subject?: string | null };
    index: number;
  }[],
  findQ: string,
  tlIndex: number,
): string {
  const q = (findQ ?? "").trim();
  if (!q) return "";
  const hits = findHitIndices(filteredTimeline, findQ);
  if (!hits.length) return "0/0";
  const i = hits.indexOf(tlIndex);
  const current = i < 0 ? 1 : i + 1;
  return `${current}/${hits.length}`;
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
