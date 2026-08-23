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

/** WhatsApp or omitted platform: keep export wall-clock digits, do not Date-convert. */
function wallClockDigits(platform?: string | null): boolean {
  return !platform || platform.toLowerCase() === "whatsapp";
}

/** Host calendar day key (`YYYY-MM-DD`); WhatsApp / omitted uses stored date digits. */
export function localDay(iso: string | null | undefined, platform?: string | null): string {
  if (!iso) return "";
  if (wallClockDigits(platform)) {
    const day = iso.slice(0, 10);
    return /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : "";
  }
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

/** Day heading as day/month/year; WhatsApp / omitted uses stored date digits. */
export function localDayLabel(iso: string | null | undefined, platform?: string | null): string {
  if (!iso) return "";
  if (wallClockDigits(platform)) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso.slice(0, 10));
    return m ? `${m[3]}/${m[2]}/${m[1]}` : "";
  }
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()}`;
}

/** Hour:minute for bubble captions; WhatsApp / omitted uses stored T digits. */
export function utcTime(iso: string | null | undefined, platform?: string | null): string {
  if (!iso) return "";
  if (wallClockDigits(platform)) {
    const t = iso.split("T")[1];
    return t && t.length >= 5 ? t.slice(0, 5) : "";
  }
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

/** Short people-row time (`11 Aug 14:32`); WhatsApp / omitted uses stored wall-clock digits. */
export function humanTime(iso: string | null | undefined, platform?: string | null): string {
  if (!iso) return "";
  if (wallClockDigits(platform)) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso.slice(0, 10));
    if (!m) return "";
    const monthIdx = Number(m[2]) - 1;
    if (monthIdx < 0 || monthIdx > 11) return "";
    const t = iso.split("T")[1];
    if (!t || t.length < 5) return "";
    return `${Number(m[3])} ${MONTHS[monthIdx]} ${t.slice(0, 5)}`;
  }
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const monthIdx = d.getMonth();
  if (monthIdx < 0 || monthIdx > 11) return "";
  return `${d.getDate()} ${MONTHS[monthIdx]} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}
