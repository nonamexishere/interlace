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

/**
 * Short UTC display for people-list `last_activity_at` (e.g. `11 Aug 14:32`).
 * Archive / API JSON stay ISO — do not rewrite stored timestamps.
 */
export function humanTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const t = iso.indexOf("T");
  if (t < 10 || iso.length < t + 6) return "";
  const [ys, ms, ds] = iso.slice(0, 10).split("-");
  const monthIdx = Number(ms) - 1;
  if (!ys || monthIdx < 0 || monthIdx > 11 || !ds) return "";
  const day = String(Number(ds));
  if (!day || day === "NaN") return "";
  const hm = iso.slice(t + 1, t + 6);
  if (!/^\d{2}:\d{2}$/.test(hm)) return "";
  return `${day} ${MONTHS[monthIdx]} ${hm}`;
}
