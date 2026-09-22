import { api } from "./api";
import { JUMP_DAY_PAGE_CAP, TIMELINE_PAGE_LIMIT } from "./jumpDay";

/** Older pages for one ← press. The list is not touched until the caller applies `rows` once. */
export async function collectOlderThreadRows<T extends ThreadRow>(
  args: CollectOlderArgs<T>,
): Promise<CollectOlderResult<T>> {
  const seen = new Set(args.knownIds());
  const origin = args.oldestCursor();
  let before = origin;
  let older: T[] = [];
  let pages = 0;
  while (pages < JUMP_DAY_PAGE_CAP) {
    if (!args.alive()) return { rows: older, exhausted: false, cancelled: true };
    if (!args.oldestCursor()) return { rows: older, exhausted: true, cancelled: false };
    if (args.oldestCursor() !== origin) {
      return { rows: older, exhausted: false, cancelled: true };
    }
    if (!before) return { rows: older, exhausted: true, cancelled: false };
    const page = await args.fetchPage(before);
    if (!args.alive()) return { rows: older, exhausted: false, cancelled: true };
    if (page.length === 0) return { rows: older, exhausted: true, cancelled: false };
    const chrono = page.toReversed().filter((row) => !seen.has(row.message_id));
    if (chrono.length === 0) return { rows: older, exhausted: true, cancelled: false };
    for (const row of chrono) seen.add(row.message_id);
    older = chrono.concat(older);
    const next = oldestSentAt(older);
    if (!next || next === before) return { rows: older, exhausted: true, cancelled: false };
    before = next;
    if (hasOlderPhoto(older.filter(args.keeps))) {
      return {
        rows: older,
        exhausted: page.length < TIMELINE_PAGE_LIMIT,
        cancelled: false,
      };
    }
    if (page.length < TIMELINE_PAGE_LIMIT) return { rows: older, exhausted: true, cancelled: false };
    pages += 1;
  }
  return { rows: older, exhausted: true, cancelled: false };
}

function oldestSentAt(rows: { sent_at?: string | null }[]): string | null {
  for (const row of rows) {
    if (row.sent_at) return row.sent_at;
  }
  return null;
}

function hasOlderPhoto(rows: ThreadRow[]): boolean {
  for (const row of rows) {
    for (const attachment of row.attachments ?? []) {
      if (isThreadStep(attachment)) return true;
    }
  }
  return false;
}

export type ThreadTarget = { message_id: number; attachment_id: number };

export type ThreadAttach = {
  id: number;
  cas_hash?: string | null;
  filename?: string | null;
  mime?: string | null;
  kind: string;
  omitted: boolean;
  missing: boolean;
};

export type ThreadItem = {
  message_id: number;
  attachment_id: number;
  hash: string;
};

export type ThreadRow = {
  message_id: number;
  sent_at?: string | null;
  attachments?: ThreadAttach[] | null;
};

type CollectOlderArgs<T extends ThreadRow> = {
  oldestCursor: () => string | null;
  knownIds: () => number[];
  fetchPage: (before: string) => Promise<T[]>;
  keeps: (row: T) => boolean;
  alive: () => boolean;
};

type CollectOlderResult<T extends ThreadRow> = {
  rows: T[];
  exhausted: boolean;
  cancelled: boolean;
};

function hashOf(a: ThreadAttach): string {
  return a.cas_hash || "";
}

function isVideoStep(a: ThreadAttach): boolean {
  const mime = (a.mime || "").toLowerCase();
  const name = (a.filename || "").toLowerCase();
  return a.kind === "video" || mime.startsWith("video/") || /\.(mp4|mov|mkv|avi|webm)$/.test(name);
}

function isPdfStep(a: ThreadAttach): boolean {
  const mime = (a.mime || "").toLowerCase();
  const name = (a.filename || "").toLowerCase();
  return mime === "application/pdf" || name.endsWith(".pdf");
}

function isVoiceStep(a: ThreadAttach): boolean {
  const mime = (a.mime || "").toLowerCase();
  const name = (a.filename || "").toLowerCase();
  return a.kind === "voice" || mime.startsWith("audio/") || /\.(opus|ogg|mp3|m4a|aac|wav)$/.test(name);
}

/** Stored image or image sticker. Not omitted, missing, empty hash, video, PDF, or voice. */
export function isThreadStep(a: ThreadAttach): boolean {
  if (a.omitted || a.missing) return false;
  if (!hashOf(a)) return false;
  if (isVideoStep(a) || isPdfStep(a) || isVoiceStep(a)) return false;
  const mime = (a.mime || "").toLowerCase();
  const name = (a.filename || "").toLowerCase();
  return (
    a.kind === "image" ||
    a.kind === "sticker" ||
    mime.startsWith("image/") ||
    /\.(jpe?g|png|gif|webp|bmp)$/.test(name)
  );
}

export function threadImages(
  filteredTimeline: { row: { message_id: number; attachments?: ThreadAttach[] | null } }[],
): ThreadItem[] {
  const steps: ThreadItem[] = [];
  for (const item of filteredTimeline) {
    for (const a of item.row.attachments ?? []) {
      if (!isThreadStep(a)) continue;
      const hash = hashOf(a);
      if (!hash) continue;
      steps.push({ message_id: item.row.message_id, attachment_id: a.id, hash });
    }
  }
  return steps;
}

export function threadIndex(steps: ThreadItem[], target: ThreadTarget): number {
  for (let i = 0; i < steps.length; i += 1) {
    const step = steps[i];
    if (step.message_id === target.message_id && step.attachment_id === target.attachment_id) return i;
  }
  return -1;
}

export async function readThreadPhoto(hash: string): Promise<string | null> {
  if (!hash) return null;
  try {
    const url = await api.casDataUrl(hash);
    return url || null;
  } catch {
    return null;
  }
}

