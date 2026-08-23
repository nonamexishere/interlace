const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

/**
 * Host calendar day key (`YYYY-MM-DD`) of an RFC3339 UTC `sent_at`.
 * Empty if missing or unparseable. Storage stays UTC ISO.
 */
export function localDay(iso: string | null | undefined) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

/** Host day heading as day/month/year. Empty if `sent_at` is missing. */
export function localDayLabel(iso: string | null | undefined) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()}`;
}

/** Host hour:minute from RFC3339 `sent_at`. Empty if missing. */
export function utcTime(iso: string | null | undefined) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

/**
 * Short host-TZ display for people-list `last_activity_at` (e.g. `11 Aug 14:32`).
 * Archive / API JSON stay ISO UTC — do not rewrite stored timestamps.
 */
export function humanTime(iso: string | null | undefined) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const monthIdx = d.getMonth();
  if (monthIdx < 0 || monthIdx > 11) return "";
  return `${d.getDate()} ${MONTHS[monthIdx]} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}
