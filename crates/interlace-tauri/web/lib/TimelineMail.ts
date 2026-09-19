/** Gmail / email_thread rows get subject title + quote fold; WA stays plain. */
export function isMailRow(row: {
  platform?: string | null;
  conversation_kind?: string | null;
}): boolean {
  const p = (row.platform ?? "").trim().toLowerCase();
  const k = (row.conversation_kind ?? "").trim().toLowerCase();
  return p === "gmail" || k === "email_thread";
}

export function displayBody(s: string) {
  return s.replace(/<attached:\s*[^>]+>/gi, "").trim();
}

/** ⌘C of N ids: in-memory timeline[] by message_id, sent_at then id, blank-line joined. */
export function joinSelectedBodies(
  timeline: { message_id: number; sent_at?: string | null; body_text: string; subject?: string | null }[],
  selectedIds: Set<number>,
): string {
  return timeline
    .filter((row) => selectedIds.has(row.message_id))
    .sort((a, b) => {
      const sa = a.sent_at ?? "";
      const sb = b.sent_at ?? "";
      if (sa < sb) return -1;
      if (sa > sb) return 1;
      return a.message_id - b.message_id;
    })
    .map((row) => displayBody(row.body_text || row.subject || ""))
    .join("\n\n");
}

/**
 * Split mail body into main + quoted tail.
 * Markers: a line `On … wrote:` or lines starting with `>`.
 */
export function splitQuotedBody(body: string): { main: string; quoted: string } {
  const text = body ?? "";
  if (!text) return { main: "", quoted: "" };

  const onWrote = /(?:^|\n)(On .+ wrote:\s*(?:\n|$))/;
  const m = text.match(onWrote);
  if (m && m.index !== undefined) {
    const splitIdx = m.index + (text[m.index] === "\n" ? 1 : 0);
    const main = text.slice(0, splitIdx).trimEnd();
    const quoted = text.slice(splitIdx);
    if (quoted.trim()) return { main, quoted };
  }

  const lines = text.split("\n");
  let firstQuote = -1;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].startsWith(">")) {
      firstQuote = i;
      break;
    }
  }
  if (firstQuote > 0) {
    return {
      main: lines.slice(0, firstQuote).join("\n").trimEnd(),
      quoted: lines.slice(firstQuote).join("\n"),
    };
  }
  if (firstQuote === 0) {
    return { main: "", quoted: text };
  }
  return { main: text, quoted: "" };
}

/** Pretty platform labels for chips and the filter toolbar. */
export function platformLabel(platform: string | null | undefined) {
  const p = (platform ?? "").trim().toLowerCase();
  if (p === "whatsapp") return "WhatsApp";
  if (p === "gmail") return "Gmail";
  if (p === "contacts") return "Contacts";
  if (!p) return "";
  return p.charAt(0).toUpperCase() + p.slice(1);
}

/** Consecutive filtered rows: same side, conversation, and host calendar day. */
export function isGroupedFollower(
  filteredTimeline: { row: { from_me: boolean; conversation_id: number; sent_at: string | null; platform: string | null }; index: number }[],
  i: number,
  localDay: (sentAt: string | null, platform: string | null) => string,
): boolean {
  if (i <= 0) return false;
  const pos = filteredTimeline.findIndex((item) => item.index === i);
  if (pos >= 0) i = pos;
  const cur = filteredTimeline[i];
  const prev = filteredTimeline[i - 1];
  if (!cur || !prev) return false;
  return (
    cur.row.from_me === prev.row.from_me &&
    cur.row.conversation_id === prev.row.conversation_id &&
    localDay(cur.row.sent_at, cur.row.platform) === localDay(prev.row.sent_at, prev.row.platform)
  );
}

/** Pretty conversation-kind labels for the kind filter toolbar. */
export function kindLabel(kind: string | null | undefined) {
  const k = (kind ?? "").trim().toLowerCase();
  if (k === "dm") return "DMs";
  if (k === "email_thread") return "Email threads";
  if (k === "group") return "Groups";
  if (!k) return "";
  return k.charAt(0).toUpperCase() + k.slice(1);
}

type AttachKindRef = { kind?: string | null; mime?: string | null };

function attachKindOf(a: AttachKindRef): string {
  return (a.kind ?? "").trim().toLowerCase();
}

function attachMimeOf(a: AttachKindRef): string {
  return (a.mime ?? "").trim().toLowerCase();
}

function isPhotosAttach(a: AttachKindRef): boolean {
  const k = attachKindOf(a);
  const mime = attachMimeOf(a);
  return k === "image" || k === "sticker" || ((k === "inline" || k === "file") && mime.startsWith("image/"));
}

function isVideoAttach(a: AttachKindRef): boolean {
  const k = attachKindOf(a);
  const mime = attachMimeOf(a);
  return k === "video" || ((k === "inline" || k === "file") && mime.startsWith("video/"));
}

function isVoiceAttach(a: AttachKindRef): boolean {
  const k = attachKindOf(a);
  const mime = attachMimeOf(a);
  return k === "voice" || ((k === "inline" || k === "file") && mime.startsWith("audio/"));
}

function isFilesAttach(a: AttachKindRef): boolean {
  const k = attachKindOf(a);
  return (k === "file" || k === "vcf") && !isPhotosAttach(a) && !isVideoAttach(a) && !isVoiceAttach(a);
}

/** Client AND for attachKindFilter (same predicates as person_timeline EXISTS). */
export function rowMatchesAttachKind(
  row: { attachments?: AttachKindRef[] | null },
  attachKind: string,
): boolean {
  if (attachKind === "all") return true;
  const atts = row.attachments ?? [];
  if (attachKind === "photos") return atts.some(isPhotosAttach);
  if (attachKind === "video") return atts.some(isVideoAttach);
  if (attachKind === "voice") return atts.some(isVoiceAttach);
  if (attachKind === "files") return atts.some(isFilesAttach);
  return false;
}
