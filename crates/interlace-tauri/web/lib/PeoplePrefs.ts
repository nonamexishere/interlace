export const SIDEBAR_PREF = "interlace.peopleSidebarCollapsed";
export const DENSITY_PREF = "interlace.density";
export const LAST_VIEW_PREF = "interlace.lastView";
export const LAST_PERSON_PREF = "interlace.lastPersonId";
export const INCLUDE_GROUPS_PREF = "interlace.includeGroups";
export const PEOPLE_SORT_PREF = "interlace.peopleSort";
export type PeopleSort = "recent" | "az";
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
