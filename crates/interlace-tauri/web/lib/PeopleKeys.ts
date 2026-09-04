import { tick } from "svelte";
import { togglePlay } from "./CasVoice";
import { nearestVisibleTlIndex } from "./PeopleUndo";

export type PeopleKeyCtx = {
  commandOpen: boolean;
  setCommandOpen: (v: boolean) => void;
  view: string;
  setView: (v: "people" | "search" | "review" | "import" | "doctor") => void;
  sidebarCollapsed: boolean;
  persistSidebar: (next: boolean) => void;
  showPersonChrome: boolean;
  setShowPersonChrome: (v: boolean) => void;
  personInspectorAttr: string;
  closeCopyMenu: () => void; copySelected: () => void;
  whenSearchPaneReady: () => Promise<HTMLInputElement | null>;
  filteredIds: number[];
  selectedId: number | null;
  selectPerson: (id: number) => void;
  prependOlder: () => void;
  visibleTlIndices: number[];
  tlIndex: number;
  setTlIndex: (n: number) => void;
  ensureTlIndexVisible: (n: number) => void;
  scrollToLatest: () => void;
};

export function handleAppKey(e: KeyboardEvent, ctx: PeopleKeyCtx) {
  const t = e.target as HTMLElement | null;
  const digit = e.key >= "1" && e.key <= "5" ? e.key : /^Digit[1-5]$/.test(e.code) ? e.code.slice(5) : "";
  const mod = e.metaKey || (e.ctrlKey && !e.altKey);
  const slashKey = e.key === "\\" || e.code === "Backslash" || e.code === "IntlBackslash";
  if (ctx.commandOpen && e.key === "Escape") {
    e.preventDefault();
    const commandOpen = false;
    ctx.setCommandOpen(commandOpen);
    return;
  }
  if (ctx.commandOpen && t?.closest?.("[data-command-palette]")) return;
  if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) {
    if (!(mod && (e.key === "f" || e.key === "F" || e.key === "k" || e.key === "K" || slashKey || e.code === "Backslash" || e.code === "IntlBackslash" || digit !== ""))) {
      if (e.key === "Escape") t.blur();
      return;
    }
  }
  if (mod && (e.key === "k" || e.key === "K")) {
    e.preventDefault();
    const commandOpen = true;
    ctx.setCommandOpen(commandOpen);
    return;
  }
  if (mod && (e.key === "f" || e.key === "F")) {
    e.preventDefault();
    if (ctx.view === "people" && ctx.selectedId) {
      const el = document.querySelector("[data-tl-find]") as HTMLInputElement | null;
      el?.focus();
      return;
    }
    void ctx.whenSearchPaneReady().then((qEl) => qEl?.focus());
    return;
  }
  if (mod && slashKey) {
    e.preventDefault();
    ctx.persistSidebar(!ctx.sidebarCollapsed);
    return;
  }
  if (mod && digit !== "") {
    e.preventDefault();
    const tabs = ["people", "search", "review", "import", "doctor"] as const;
    const next = tabs[Number(digit) - 1];
    if (next) ctx.setView(next);
    return;
  }
  if (e.key === "Escape") {
    if (document.querySelector("[data-context-menu]")) {
      e.preventDefault();
      ctx.closeCopyMenu();
      return;
    }
    const ae = document.activeElement as HTMLElement | null;
    if (ctx.showPersonChrome && ae?.closest?.(`[${ctx.personInspectorAttr}]`)) {
      e.preventDefault();
      const showPersonChrome = false;
      ctx.setShowPersonChrome(showPersonChrome);
      return;
    }
    const view = "people";
    ctx.setView(view);
    return;
  }
  if (ctx.view !== "people") return;
  if (e.key === "/") {
    e.preventDefault();
    document.getElementById("person-filter")?.focus();
    return;
  }
  const inPeopleList =
    (t?.closest?.("[role='listbox']") || t?.getAttribute?.("role") === "option") &&
    t?.id !== "person-filter" &&
    t?.tagName !== "INPUT";
  if ((e.key === " " || e.code === "Space") && !(e.metaKey || e.ctrlKey || e.altKey) && ctx.selectedId && !inPeopleList) {
    if (t?.tagName === "BUTTON" || t?.tagName === "VIDEO") return;
    if (document.querySelector("[data-photo-lightbox],[data-cas-video-overlay]")) return;
    const audio = document.querySelector(`#person-timeline [data-tl-index="${ctx.tlIndex}"] [data-voice-note] audio`);
    if (audio) { e.preventDefault(); if (!e.repeat) togglePlay(audio); }
    return;
  }
  if (e.key === "End" && ctx.selectedId && !inPeopleList) {
    e.preventDefault();
    ctx.scrollToLatest();
    return;
  }
  if (inPeopleList && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
    e.preventDefault();
    const filtered = ctx.filteredIds;
    const ids = filtered;
    if (!ids.length) return;
    const cur = ctx.selectedId != null ? ids.indexOf(ctx.selectedId) : -1;
    const next =
      e.key === "ArrowDown"
        ? Math.min(ids.length - 1, Math.max(0, cur) + (cur < 0 ? 0 : 1))
        : Math.max(0, cur < 0 ? 0 : cur - 1);
    if (ids[next] === ctx.selectedId) return;
    ctx.selectPerson(ids[next]);
    void tick().then(() => {
      const box = document.querySelector("[role='listbox'][aria-label='People']");
      const opt = box?.querySelector("[role='option'][aria-selected='true']") as HTMLElement | null;
      opt?.focus();
    });
    return;
  }
  if (ctx.selectedId && !inPeopleList && (e.code === "Home" || (mod && e.key === "ArrowUp"))) {
    e.preventDefault(); e.stopPropagation();
    const atBtn = !!t?.closest?.("[data-load-older]");
    const first = document.querySelector("#person-timeline [data-tl-index]");
    const oldest = first ? Number(first.getAttribute("data-tl-index")) : NaN;
    if (atBtn || ctx.tlIndex === oldest) ctx.prependOlder();
    return;
  }
  if (mod && (e.key === "c" || e.key === "C") && ctx.selectedId && !inPeopleList) {
    e.preventDefault(); ctx.copySelected(); return;
  }
  const visible = ctx.visibleTlIndices;
  if (!visible.length) return;
  let pos = visible.indexOf(ctx.tlIndex);
  if (pos < 0) {
    const snapped = nearestVisibleTlIndex(ctx.tlIndex, visible);
    ctx.setTlIndex(snapped);
    pos = visible.indexOf(snapped);
  }
  if (e.key === "j" || (!inPeopleList && e.key === "ArrowDown")) {
    if (pos >= 0 && pos < visible.length - 1) {
      const next = visible[pos + 1];
      ctx.setTlIndex(next);
      ctx.ensureTlIndexVisible(next);
    }
    e.preventDefault();
  }
  if (e.key === "k" || (!inPeopleList && !e.metaKey && e.key === "ArrowUp")) {
    if (pos > 0) {
      const next = visible[pos - 1];
      ctx.setTlIndex(next);
      ctx.ensureTlIndexVisible(next);
    }
    e.preventDefault();
  }
}

/** Capture-only: block WKWebView Home / ⌘↑ scroll-to-top. No stopPropagation. */
export function preventNativeHomeScroll(e: KeyboardEvent, selectedId?: number | null) {
  const t = e.target as HTMLElement | null;
  if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.closest?.("[data-command-palette]"))) return;
  if (selectedId == null && !document.getElementById("person-timeline")) return;
  const mod = e.metaKey || (e.ctrlKey && !e.altKey);
  if (e.code === "Home" || (mod && e.key === "ArrowUp")) e.preventDefault();
}
