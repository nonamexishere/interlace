/** Segment of a search snippet: plain text or FTS-matched mark. */
export type SnippetSegment =
  | { kind: "text"; text: string }
  | { kind: "mark"; text: string };

const ATTACHED_NOISE = /<attached:\s*[^>]+>/gi;
/** Core FTS wraps hits with «…» (snippet(…, '«', '»', …)). */
const FTS_MARK = /«([^»]*)»/g;

/**
 * Split a core FTS snippet into plain-text + mark segments.
 * Never returns HTML strings — callers render <mark> as Svelte elements.
 */
export function splitSnippet(raw: string): SnippetSegment[] {
  const cleaned = (raw || "").replace(ATTACHED_NOISE, "").trim();
  if (!cleaned) return [];

  const segments: SnippetSegment[] = [];
  let last = 0;
  FTS_MARK.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = FTS_MARK.exec(cleaned)) !== null) {
    if (m.index > last) {
      segments.push({ kind: "text", text: cleaned.slice(last, m.index) });
    }
    segments.push({ kind: "mark", text: m[1] ?? "" });
    last = m.index + m[0].length;
  }
  if (last < cleaned.length) {
    segments.push({ kind: "text", text: cleaned.slice(last) });
  }
  if (segments.length === 0) {
    segments.push({ kind: "text", text: cleaned });
  }
  return segments;
}
