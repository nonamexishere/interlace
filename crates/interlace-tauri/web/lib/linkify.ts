/** Segment of a timeline body: plain text or an http(s) URL. */
export type UrlSegment =
  | { kind: "text"; text: string }
  | { kind: "url"; text: string };

/** Only http(s). Acceptance: https://example.com/a */
const HTTP_URL = /https?:\/\/[^\s<>"'`]+/gi;

/**
 * Split a bubble body into plain-text + http(s) URL segments.
 * Never returns HTML strings — callers render <a> as Svelte elements.
 */
export function splitUrls(raw: string): UrlSegment[] {
  const text = raw ?? "";
  if (!text) return [];

  const segments: UrlSegment[] = [];
  let last = 0;
  HTTP_URL.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = HTTP_URL.exec(text)) !== null) {
    let url = m[0].replace(/[.,;:!?]+$/, "");
    if (!url) continue;
    if (m.index > last) {
      segments.push({ kind: "text", text: text.slice(last, m.index) });
    }
    segments.push({ kind: "url", text: url });
    last = m.index + url.length;
    HTTP_URL.lastIndex = last;
  }
  if (last < text.length) {
    segments.push({ kind: "text", text: text.slice(last) });
  }
  if (segments.length === 0) {
    segments.push({ kind: "text", text });
  }
  return segments;
}
