export const SIDEBAR_PREF = "interlace.peopleSidebarCollapsed";
export const DENSITY_PREF = "interlace.density";
export const LAST_VIEW_PREF = "interlace.lastView";
export const LAST_PERSON_PREF = "interlace.lastPersonId";
export const INCLUDE_GROUPS_PREF = "interlace.includeGroups";
export const PEOPLE_SORT_PREF = "interlace.peopleSort";
export const PEOPLE_PINS_PREF = "interlace.peoplePins";
export const LAST_READ_PREF = "interlace.lastRead";
export type PeopleSort = "recent" | "az";
export type PeoplePinsMap = { [archive_id: string]: number[] };
export type LastReadMap = { [archive_id: string]: { [personId: string]: number } };
export type LastView = "people" | "search" | "review" | "import" | "doctor";
export const LAST_VIEWS: readonly LastView[] = [
  "people",
  "search",
  "review",
  "import",
  "doctor",
];
export type Density = "default" | "comfortable";

export function readSidebarPref(): boolean {
  return localStorage.getItem(SIDEBAR_PREF) === "1";
}

export function writeSidebarPref(next: boolean) {
  localStorage.setItem(SIDEBAR_PREF, next ? "1" : "0");
}

export function readIncludeGroupsPref(): boolean {
  return localStorage.getItem(INCLUDE_GROUPS_PREF) === "1";
}

export function writeIncludeGroupsPref(next: boolean) {
  localStorage.setItem(INCLUDE_GROUPS_PREF, next ? "1" : "0");
}

export function readPeopleSortPref(): PeopleSort {
  return localStorage.getItem(PEOPLE_SORT_PREF) === "az" ? "az" : "recent";
}

export function writePeopleSortPref(next: PeopleSort) {
  localStorage.setItem(PEOPLE_SORT_PREF, next);
}

export function readPeoplePinsPref(): PeoplePinsMap {
  const raw = localStorage.getItem(PEOPLE_PINS_PREF);
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    const out: PeoplePinsMap = {};
    for (const [archive_id, val] of Object.entries(parsed)) {
      if (!Array.isArray(val)) continue;
      out[archive_id] = val.filter((id): id is number => typeof id === "number" && Number.isFinite(id));
    }
    return out;
  } catch {
    return {};
  }
}

export function writePeoplePinsPref(next: PeoplePinsMap) {
  localStorage.setItem(PEOPLE_PINS_PREF, JSON.stringify(next));
}

export function pinsForArchive(archive_id: string): number[] {
  if (!archive_id) return [];
  return readPeoplePinsPref()[archive_id] ?? [];
}

export function togglePersonPin(archive_id: string, personId: number): number[] {
  if (!archive_id) return [];
  const all = readPeoplePinsPref();
  const cur = all[archive_id] ?? [];
  const next = cur.includes(personId) ? cur.filter((id) => id !== personId) : [...cur, personId];
  all[archive_id] = next;
  writePeoplePinsPref(all);
  return next;
}

export function readLastReadPref(): LastReadMap {
  const raw = localStorage.getItem(LAST_READ_PREF);
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    const out: LastReadMap = {};
    for (const [archive_id, val] of Object.entries(parsed)) {
      if (!val || typeof val !== "object" || Array.isArray(val)) continue;
      const inner: { [personId: string]: number } = {};
      for (const [personId, mid] of Object.entries(val as Record<string, unknown>)) {
        if (typeof mid === "number" && Number.isFinite(mid)) inner[personId] = mid;
      }
      out[archive_id] = inner;
    }
    return out;
  } catch {
    return {};
  }
}

export function writeLastReadPref(next: LastReadMap) {
  localStorage.setItem(LAST_READ_PREF, JSON.stringify(next));
}

export function lastReadFor(archive_id: string, personId: number): number | undefined {
  if (!archive_id) return undefined;
  return readLastReadPref()[archive_id]?.[String(personId)];
}

export function persistLastRead(archive_id: string, personId: number, message_id: number) {
  if (!archive_id) return;
  if (!Number.isFinite(message_id)) return;
  const all = readLastReadPref();
  const inner = { ...(all[archive_id] ?? {}) };
  inner[String(personId)] = message_id;
  all[archive_id] = inner;
  writeLastReadPref(all);
}

export function readDensityPref(): Density {
  return localStorage.getItem(DENSITY_PREF) === "comfortable" ? "comfortable" : "default";
}

export function writeDensityPref(next: Density) {
  localStorage.setItem(DENSITY_PREF, next);
}

export function writeLastView(view: string) {
  localStorage.setItem(LAST_VIEW_PREF, view);
}

export function writeLastPerson(id: number) {
  localStorage.setItem(LAST_PERSON_PREF, String(id));
}

export function readLastView(): LastView {
  const rawView = localStorage.getItem(LAST_VIEW_PREF);
  return LAST_VIEWS.includes(rawView as LastView) ? (rawView as LastView) : "people";
}

export function readLastPersonId(): number | null {
  const rawId = localStorage.getItem(LAST_PERSON_PREF);
  const id = rawId ? Number(rawId) : NaN;
  return Number.isFinite(id) ? id : null;
}
