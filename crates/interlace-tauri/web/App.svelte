<script lang="ts">
  import { onMount, tick } from "svelte";
  import { fly } from "svelte/transition";
  import { listen } from "@tauri-apps/api/event";
  import { getCurrentWebview } from "@tauri-apps/api/webview";
  import { getCurrentWindow } from "@tauri-apps/api/window";
  import { api, type Identity, type LinkEvent, type Person, type PersonConversation, type Status, type TimelineRow } from "./lib/api";
  import { mergeTargets } from "./lib/utils";
  import { humanTime, localDay, localDayLabel, utcTime } from "./lib/formatTime";
  import { splitUrls } from "./lib/linkify";
  import LinkifyBody from "./lib/LinkifyBody.svelte";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Card } from "$lib/components/ui/card/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Label } from "$lib/components/ui/label/index.js";
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import { Separator } from "$lib/components/ui/separator/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import { Toast } from "$lib/components/ui/toast/index.js";
  import ConfirmDialog from "$lib/ConfirmDialog.svelte";
  import CommandPalette from "$lib/CommandPalette.svelte";
  import SearchPane from "$lib/SearchPane.svelte";
  import ReviewPane from "$lib/ReviewPane.svelte";
  import ImportPane from "$lib/ImportPane.svelte";
  import DoctorPane from "$lib/DoctorPane.svelte";
  import EmptyState from "$lib/EmptyState.svelte";
  import CasAttach from "$lib/CasAttach.svelte";
  import { t } from "$lib/i18n";
  import { chromeMotionMs } from "$lib/motion";
  import PanelLeft from "@lucide/svelte/icons/panel-left";
  import PanelLeftClose from "@lucide/svelte/icons/panel-left-close";
  import User from "@lucide/svelte/icons/user";

  let err = $state("");
  let setup = $state(true);
  let st = $state<Status | null>(null);
  let region = $state("");
  let name = $state("");
  let emails = $state("");
  let phones = $state("");
  let people = $state<Person[]>([]);
  let filter = $state("");
  let selectedId = $state<number | null>(null);
  let personTitle = $state("Select a person");
  let identities = $state<Identity[]>([]);
  let timeline = $state<TimelineRow[]>([]);
  let tlIndex = $state(0);
  let includeGroups = $state(false);
  let selectedConversationId = $state<number | null>(null);
  let conversations = $state<PersonConversation[]>([]);
  /** Timeline platform toolbar: "all" or a platform value present for this person. */
  let platformFilter = $state<string>("all");
  /** Timeline kind toolbar: "all" | "dm" | "email_thread" | "group". */
  let kindFilter = $state<string>("all");
  let showPersonChrome = $state(false);
  let mergeOpen = $state(false);
  let mergeQuery = $state("");
  let allowSelf = $state(false);
  let mergeKeepId = $state<number | null>(null);
  let mergeKeepName = $state("");
  const mergeList = $derived(
    mergeKeepId == null
      ? []
      : mergeTargets(people, mergeKeepId, allowSelf, mergeQuery),
  );
  let events = $state<LinkEvent[]>([]);
  const UNDOABLE = new Set(["merge_persons", "link", "unlink"]);
  const undoableEvents = $derived.by(() => {
    const undone = new Set(
      events
        .filter((e) => e.op === "split_person" && e.undo_of != null)
        .map((e) => e.undo_of as number),
    );
    return events.filter(
      (e) => UNDOABLE.has(e.op) && e.actor === "user" && !undone.has(e.id),
    );
  });

  let confirmOpen = $state(false);
  let confirmTitle = $state("");
  let confirmDesc = $state("");
  let confirmRun = $state<(() => Promise<void>) | null>(null);
  let view = $state<"people" | "search" | "review" | "import" | "doctor">("people");
  let commandOpen = $state(false);
  let searchQ = $state("");
  let booting = $state(true);
  let opening = $state(false);
  let tlLoading = $state(false);
  let tlAppending = $state(false);
  let tlError = $state("");
  let peopleLoading = $state(true);
  let peopleGen = 0;
  let tlGen = 0;
  let doctor = $state<string[]>([]);
  let pinLatestObs: ResizeObserver | null = null;
  let pinLatestUntil: ReturnType<typeof setTimeout> | null = null;

  const cloudWarning = $derived(
    (st?.warnings ?? []).find((w) =>
      /iCloud|Mobile Documents|Dropbox|Google Drive/i.test(w),
    ),
  );

  /** Native window / Cmd-tab title: view or selected person only — never body/snippet/query. */
  const windowTitle = $derived.by(() => {
    if (setup || booting || !st) return "Interlace";
    if (view === "search") return "Search — Interlace";
    if (view === "review") return "Review — Interlace";
    if (view === "import") return "Import — Interlace";
    if (view === "doctor") return "Doctor — Interlace";
    // People: selected display name, else bare Interlace (not "People — …").
    if (selectedId != null && personTitle && personTitle !== "Select a person") {
      return personTitle + " — Interlace";
    }
    return "Interlace";
  });

  $effect(() => {
    const title = windowTitle;
    void getCurrentWindow().setTitle(title).catch(() => {});
  });

  const filtered = $derived(
    people.filter((p) => {
      const q = filter.trim().toLowerCase();
      if (!q) return true;
      let hay = (p.display_name + (p.is_self ? " self" : "")).toLowerCase();
      for (const v of p.identity_values ?? []) {
        hay += " " + v.toLowerCase();
      }
      return hay.includes(q);
    }),
  );

  const peopleTabId = $derived(
    selectedId != null && filtered.some((p) => p.id === selectedId)
      ? selectedId
      : (filtered[0]?.id ?? null),
  );

  const SIDEBAR_PREF = "interlace.peopleSidebarCollapsed";
  let userCollapsed = $state(false);
  let narrow = $state(false);
  let forceOpen = $state(false);
  const sidebarCollapsed = $derived(userCollapsed || (narrow && !forceOpen));

  function readSidebarPref(): boolean {
    return localStorage.getItem(SIDEBAR_PREF) === "1";
  }

  function persistSidebar(next: boolean) {
    userCollapsed = next;
    forceOpen = !next; // Expand → open now even if narrow
    localStorage.setItem(SIDEBAR_PREF, next ? "1" : "0");
  }

  function syncNarrow() {
    const next = window.innerWidth < 880;
    if (next && !narrow) forceOpen = false; // just crossed into narrow
    narrow = next;
  }

  const SANDBOX_DENIED =
    "macOS blocked that folder. Use Open existing\u2026 once so Interlace can remember it.";

  function friendly(raw: string) {
    if (raw === SANDBOX_DENIED || raw.includes(SANDBOX_DENIED)) {
      return SANDBOX_DENIED;
    }
    if (raw.includes("archive in use")) {
      return `Archive is locked by another Interlace window or CLI writer. Close that process and try again.\n${raw}`;
    }
    if (raw.includes("pass --locale") || raw.includes("locale vote")) {
      return `Could not guess the WhatsApp language pack. Set Locale (for example tr-TR) on the Import tab and retry.\n${raw}`;
    }
    if (raw.includes("not an Interlace archive")) {
      return `That folder is not an archive (no INTERLACE.toml). Create one or open your existing archive folder.\n${raw}`;
    }
    if (raw.includes("no archive open")) {
      return "No archive is open. An import may still be running — wait for it, or open a folder.";
    }
    return raw;
  }

  function showErr(e: unknown) {
    err = friendly(e instanceof Error ? e.message : String(e ?? ""));
  }

  let toastSeq = 0;
  let toasts = $state<{ id: number; message: string }[]>([]);

  function showToast(message: string) {
    const id = ++toastSeq;
    toasts = [...toasts, { id, message }];
    window.setTimeout(() => {
      toasts = toasts.filter((item) => item.id !== id);
    }, 2500);
  }

  /** Tauri file-drop paths only — reject http(s) and other URL schemes. */
  function isDroppedUrl(path: string): boolean {
    const s = path.trim();
    if (s.startsWith("http://") || s.startsWith("https://")) return true;
    return /^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//.test(s);
  }

  async function importDroppedPaths(paths: string[]) {
    const local = paths.find((p) => p && p.trim() && !isDroppedUrl(p));
    if (!local) {
      if (paths.some((p) => (p ?? "").trim())) {
        showToast("Drop a local ZIP or mbox — URLs are not imported.");
      }
      return;
    }
    err = "";
    view = "import";
    try {
      await api.importStart({ path: local });
    } catch (e) {
      showErr(e);
    }
  }

  function csv(s: string) {
    return s.split(",").map((x) => x.trim()).filter(Boolean);
  }

  function displayBody(s: string) {
    return s.replace(/<attached:\s*[^>]+>/gi, "").trim();
  }

  let copyMenu = $state<{ x: number; y: number; text: string } | null>(null);

  function openCopyMenu(e: MouseEvent, row: TimelineRow) {
    e.preventDefault();
    copyMenu = { x: e.clientX, y: e.clientY, text: row.body_text || row.subject || "" };
  }

  function closeCopyMenu() {
    copyMenu = null;
  }

  async function copyText() {
    if (!copyMenu) return;
    const text = displayBody(copyMenu.text);
    copyMenu = null;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      showToast("Could not copy");
    }
  }

  function onCopyMenuAway(e: MouseEvent) {
    if (!copyMenu) return;
    const el = e.target as HTMLElement | null;
    if (el?.closest("[data-copy-menu]")) return;
    closeCopyMenu();
  }

  /** Gmail / email_thread rows get subject title + quote fold; WA stays plain. */
  function isMailRow(row: {
    platform?: string | null;
    conversation_kind?: string | null;
  }): boolean {
    const p = (row.platform ?? "").trim().toLowerCase();
    const k = (row.conversation_kind ?? "").trim().toLowerCase();
    return p === "gmail" || k === "email_thread";
  }

  /**
   * Split mail body into main + quoted tail.
   * Markers: a line `On … wrote:` or lines starting with `>`.
   */
  function splitQuotedBody(body: string): { main: string; quoted: string } {
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

  /** message_id → quoted tail expanded on the person timeline. */
  let quotedOpen = $state<Record<number, boolean>>({});

  function toggleQuoted(messageId: number, e: Event) {
    e.stopPropagation();
    e.preventDefault();
    quotedOpen = { ...quotedOpen, [messageId]: !quotedOpen[messageId] };
  }

  /** Known kind order for chip toolbar (others sort after). */
  const KIND_ORDER = ["dm", "email_thread", "group"] as const;

  /**
   * Platforms present for this person (conversations + loaded timeline).
   * When a kind is selected, only platforms that appear under that kind.
   */
  const availablePlatforms = $derived.by(() => {
    const set = new Set<string>();
    for (const c of conversations) {
      if (kindFilter !== "all" && (c.kind ?? "").trim() !== kindFilter) continue;
      const p = (c.platform ?? "").trim();
      if (p) set.add(p);
    }
    for (const row of timeline) {
      if (kindFilter !== "all" && (row.conversation_kind ?? "").trim() !== kindFilter) {
        continue;
      }
      const p = (row.platform ?? "").trim();
      if (p) set.add(p);
    }
    return [...set].sort();
  });

  /**
   * Kinds present for this person (conversations.kind + timeline.conversation_kind).
   * When a platform is selected, only kinds that appear under that platform.
   */
  const availableKinds = $derived.by(() => {
    const set = new Set<string>();
    for (const c of conversations) {
      if (platformFilter !== "all" && (c.platform ?? "").trim() !== platformFilter) {
        continue;
      }
      const k = (c.kind ?? "").trim();
      if (k) set.add(k);
    }
    for (const row of timeline) {
      if (platformFilter !== "all" && (row.platform ?? "").trim() !== platformFilter) {
        continue;
      }
      const k = (row.conversation_kind ?? "").trim();
      if (k) set.add(k);
    }
    const known = KIND_ORDER.filter((k) => set.has(k));
    const rest = [...set].filter((k) => !(KIND_ORDER as readonly string[]).includes(k)).sort();
    return [...known, ...rest];
  });

  /** If the other filter removes the selected chip, snap back to All. */
  $effect(() => {
    if (platformFilter !== "all" && !availablePlatforms.includes(platformFilter)) {
      platformFilter = "all";
    }
  });
  $effect(() => {
    if (kindFilter !== "all" && !availableKinds.includes(kindFilter)) {
      kindFilter = "all";
    }
  });

  /** Client-side platform + kind filter for the loaded timeline page (AND). */
  const filteredTimeline = $derived(
    timeline
      .map((row, index) => ({ row, index }))
      .filter(
        (item) =>
          (platformFilter === "all" || item.row.platform === platformFilter) &&
          (kindFilter === "all" || item.row.conversation_kind === kindFilter),
      ),
  );

  /** Consecutive filtered rows: same side, conversation, and host calendar day. */
  function isGroupedFollower(i: number): boolean {
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

  /** Original `timeline` indices currently shown (j/k and highlight use these). */
  const visibleTlIndices = $derived(filteredTimeline.map((item) => item.index));

  /** Nearest visible index to `from` (later wins ties). */
  function nearestVisibleTlIndex(from: number, visible: number[]): number {
    if (!visible.length) return from;
    let best = visible[0];
    let bestDist = Math.abs(visible[0] - from);
    for (let i = 1; i < visible.length; i++) {
      const idx = visible[i];
      const d = Math.abs(idx - from);
      if (d < bestDist || (d === bestDist && idx > best)) {
        best = idx;
        bestDist = d;
      }
    }
    return best;
  }

  /** Keep selection ring on a row that is actually rendered. */
  $effect(() => {
    const visible = visibleTlIndices;
    // Jump miss sets tlIndex < 0 (no ring); do not claim a visible row.
    if (tlIndex < 0) return;
    if (!visible.length) return;
    if (!visible.includes(tlIndex)) {
      tlIndex = nearestVisibleTlIndex(tlIndex, visible);
    }
  });

  /** Unmeasured slots use constant ESTIMATED_ROW_HEIGHT (88). */
  const ESTIMATED_ROW_HEIGHT = 88;
  const OVERSCAN = 15;
  /** One import page is 80 rows. Do not virtualize that — spacers hitch. */
  const VIRTUALIZE_AFTER = 250;
  let tlScrollTop = $state(0);
  let tlViewportHeight = $state(480);
  /** Load-older + window-start day heading — not in rowHeights. */
  let tlChromeHeight = $state(0);
  /** Measured heights keyed by original timeline index (`item.index` / data-tl-index). */
  let rowHeights = $state<Record<number, number>>({});
  let userScrolling = false;
  let userScrollUntil: ReturnType<typeof setTimeout> | null = null;
  let programmaticScroll = false;
  let pointerOnTimeline = false;

  function markUserScrolling() {
    userScrolling = true;
    if (userScrollUntil != null) clearTimeout(userScrollUntil);
    userScrollUntil = setTimeout(() => {
      userScrolling = false;
      userScrollUntil = null;
    }, 150);
  }

  function writeScrollTop(sc: HTMLElement, top: number) {
    programmaticScroll = true;
    sc.scrollTop = top;
    tlScrollTop = sc.scrollTop;
    tlViewportHeight = sc.clientHeight || tlViewportHeight;
    programmaticScroll = false;
  }

  function rowOffsetInPane(sc: HTMLElement, el: HTMLElement): number {
    return el.getBoundingClientRect().top - sc.getBoundingClientRect().top + sc.scrollTop;
  }

  function measureOuterHeight(el: HTMLElement): number {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return Math.round(
      r.height + (parseFloat(cs.marginTop) || 0) + (parseFloat(cs.marginBottom) || 0),
    );
  }

  function measureTimelineChrome(sc: HTMLElement): number {
    let h = 0;
    const older = sc.querySelector("[data-load-older]");
    if (older instanceof HTMLElement) h += measureOuterHeight(older);
    const heading = sc.querySelector(".day-heading");
    if (heading instanceof HTMLElement) h += measureOuterHeight(heading);
    return h;
  }

  function heightOf(orig: number): number {
    return rowHeights[orig] ?? ESTIMATED_ROW_HEIGHT;
  }

  function offsetOf(filteredPos: number): number {
    const rows = filteredTimeline;
    const n = Math.max(0, Math.min(filteredPos, rows.length));
    let sum = 0;
    for (let k = 0; k < n; k++) {
      sum += heightOf(rows[k].index);
    }
    return sum;
  }

  function onTimelineScroll(e: Event) {
    const el = e.currentTarget as HTMLElement | null;
    if (!el) return;
    tlScrollTop = el.scrollTop;
    tlViewportHeight = el.clientHeight || tlViewportHeight;
    if (programmaticScroll) return;
    if (!pointerOnTimeline) return;
    markUserScrolling();
    if (pinLatestObs && el.scrollTop + el.clientHeight < el.scrollHeight - 4) {
      stopPinLatest();
    }
  }

  function onTimelineWheel() {
    stopPinLatest();
    markUserScrolling();
  }

  function onTimelinePointerDown() {
    pointerOnTimeline = true;
  }

  function onTimelinePointerUp() {
    pointerOnTimeline = false;
  }

  /** Visible filtered-row index range (inclusive start, exclusive end) + overscan. */
  const visibleRange = $derived.by(() => {
    const total = filteredTimeline.length;
    if (total === 0) return { startIndex: 0, endIndex: 0 };
    // A single page (80) must mount fully. Virtualizing it is the hitch.
    if (total <= VIRTUALIZE_AFTER) return { startIndex: 0, endIndex: total };
    const vh = Math.max(tlViewportHeight, 200);
    const scrollTop = Math.max(0, tlScrollTop);
    let startIndex = 0;
    let acc = 0;
    while (startIndex < total) {
      const h = heightOf(filteredTimeline[startIndex].index);
      if (acc + h > scrollTop) break;
      acc += h;
      startIndex += 1;
    }
    let endIndex = startIndex;
    let endAcc = acc;
    const viewBottom = scrollTop + vh;
    while (endIndex < total && endAcc < viewBottom) {
      endAcc += heightOf(filteredTimeline[endIndex].index);
      endIndex += 1;
    }
    startIndex = Math.max(0, startIndex - OVERSCAN);
    endIndex = Math.min(total, endIndex + OVERSCAN);
    // Filter shrink or oversize scrollTop: keep a window on the real list.
    if (startIndex >= total) {
      const windowRows = Math.ceil(vh / ESTIMATED_ROW_HEIGHT) + OVERSCAN * 2;
      startIndex = Math.max(0, total - windowRows);
      endIndex = total;
    } else if (endIndex <= startIndex) {
      endIndex = Math.min(total, startIndex + 1);
    }
    return { startIndex, endIndex };
  });

  const spacerTop = $derived(offsetOf(visibleRange.startIndex));
  const spacerBottom = $derived(
    Math.max(0, offsetOf(filteredTimeline.length) - offsetOf(visibleRange.endIndex)),
  );

  /** Day groups for the overscan window only (headings for visible days). */
  const windowedDayGroups = $derived.by(() => {
    const startIndex = visibleRange.startIndex;
    const endIndex = visibleRange.endIndex;
    const rows = filteredTimeline.slice(startIndex, endIndex);
    const groups: { key: string; label: string; rows: { row: TimelineRow; index: number }[] }[] =
      [];
    for (let i = 0; i < rows.length; i++) {
      const { row, index } = rows[i];
      const key = localDay(row.sent_at, row.platform);
      // i === 0 starts a group so sticky day heading stays when the day began above the window.
      const dayChanged =
        i === 0 ||
        key !== localDay(rows[i - 1]?.row.sent_at, rows[i - 1]?.row.platform);
      const last = groups[groups.length - 1];
      if (!last || dayChanged) {
        groups.push({
          key,
          label: key ? localDayLabel(row.sent_at, row.platform) : "",
          rows: [{ row, index }],
        });
      } else {
        last.rows.push({ row, index });
      }
    }
    return groups;
  });

  /** Keep j/k selection on-screen when it leaves the virtual window. */
  function ensureTlIndexVisible(index: number) {
    const pos = visibleTlIndices.indexOf(index);
    if (pos < 0) return;
    const sc = document.getElementById("person-timeline");
    if (!sc) return;
    const mounted = sc.querySelector(`[data-tl-index="${index}"]`);
    const rowTop =
      mounted instanceof HTMLElement
        ? rowOffsetInPane(sc, mounted)
        : tlChromeHeight + offsetOf(pos);
    const rowH =
      mounted instanceof HTMLElement
        ? mounted.getBoundingClientRect().height
        : heightOf(filteredTimeline[pos]?.index ?? index);
    const rowBottom = rowTop + rowH;
    const viewTop = sc.scrollTop;
    const viewBottom = viewTop + sc.clientHeight;
    if (rowTop < viewTop) {
      writeScrollTop(sc, Math.max(0, rowTop - ESTIMATED_ROW_HEIGHT));
    } else if (rowBottom > viewBottom) {
      writeScrollTop(sc, rowBottom - sc.clientHeight + ESTIMATED_ROW_HEIGHT);
    }
  }

  /** Queued measures; flushed once per frame as `rowHeights = next`. */
  let pendingMeasures: Record<number, number> = {};
  let pendingChrome = false;
  let measureRaf = 0;

  function scheduleMeasureFlush() {
    if (measureRaf) return;
    measureRaf = requestAnimationFrame(flushRowMeasures);
  }

  function clearPendingMeasures() {
    pendingMeasures = {};
    if (measureRaf) {
      cancelAnimationFrame(measureRaf);
      measureRaf = 0;
    }
  }

  function scheduleChromeMeasure() {
    pendingChrome = true;
    scheduleMeasureFlush();
  }

  function applyRowMeasure(orig: number, h: number) {
    if (!(h > 0) || !Number.isFinite(h)) return;
    if ((pendingMeasures[orig] ?? rowHeights[orig]) === h) return;
    pendingMeasures[orig] = h;
    scheduleMeasureFlush();
  }

  function flushRowMeasures() {
    measureRaf = 0;
    const sc = document.getElementById("person-timeline");
    if (pendingChrome) {
      pendingChrome = false;
      if (sc) {
        const chrome = measureTimelineChrome(sc);
        if (chrome !== tlChromeHeight) tlChromeHeight = chrome;
      }
    }
    const pending = pendingMeasures;
    pendingMeasures = {};
    const next: Record<number, number> = { ...rowHeights };
    let changed = false;
    for (const key of Object.keys(pending)) {
      const orig = Number(key);
      const h = pending[orig];
      if (!(h > 0) || !Number.isFinite(h)) continue;
      if (rowHeights[orig] === h) continue;
      next[orig] = h;
      changed = true;
    }
    // Cache only. Never write scrollTop from measure — that fights the wheel.
    if (changed) rowHeights = next;
  }

  /** Per-row action: observe this node; never keyed on windowedTlKeys. */
  function measureTlRow(node: HTMLElement, orig: number) {
    const read = () => {
      const raw = node.getAttribute("data-tl-index");
      const idx = raw != null ? Number(raw) : orig;
      if (!Number.isFinite(idx)) return;
      const h = Math.round(node.getBoundingClientRect().height);
      applyRowMeasure(idx, h);
      scheduleChromeMeasure();
    };
    const obs = new ResizeObserver(read);
    obs.observe(node);
    read();
    return {
      update(nextOrig: number) {
        orig = nextOrig;
        read();
      },
      destroy() {
        obs.disconnect();
      },
    };
  }

  $effect(() => {
    void view;
    void selectedId;
    void timeline.length;
    void filteredTimeline.length;
    if (view !== "people") return;
    scheduleChromeMeasure();
  });

  function ask(title: string, description: string, run: () => Promise<void>) {
    confirmTitle = title;
    confirmDesc = description;
    confirmRun = run;
    confirmOpen = true;
  }

  function openUrl(url: string) {
    ask("Open this link?", url, async () => {
      await api.openUrl(url);
    });
  }

  async function refreshPeople() {
    const gen = ++peopleGen;
    peopleLoading = true;
    try {
      const next = await api.people();
      if (gen !== peopleGen) return;
      people = next;
    } catch (e) {
      if (gen === peopleGen) showErr(e);
    } finally {
      if (gen === peopleGen) peopleLoading = false;
    }
  }

  async function refreshEvents() {
    events = await api.linkEvents();
  }

  async function applyStatus(next: Status) {
    st = next;
    setup = false;
    // Search must not wait on a people rebuild (#270). Exclusive flock stays.
    void refreshPeople().catch(showErr);
    await refreshEvents();
    // Do not start doctorIssuesQuick here: badge stays empty until the Doctor
    // tab. Integrity/GC onDone must keep the full list (do not clear doctor).
  }

  async function openPath(path: string) {
    err = "";
    doctor = [];
    opening = true;
    try {
      await applyStatus(await api.open(path));
    } finally {
      opening = false;
    }
  }

  async function createArchive() {
    err = "";
    doctor = [];
    const r = region.trim();
    if (!r) {
      err = "phone-region is required (e.g. TR, US)";
      return;
    }
    try {
      const folder = await api.pickFolder();
      if (!folder) return;
      await applyStatus(
        await api.init({
          path: folder,
          phoneRegion: r,
          name: name.trim() || null,
          emails: csv(emails),
          phones: csv(phones),
        }),
      );
    } catch (e) {
      showErr(e);
    }
  }

  async function openPicker() {
    err = "";
    try {
      const folder = await api.pickFolder();
      if (!folder) return;
      await openPath(folder);
    } catch (e) {
      showErr(e);
    }
  }

  function stopPinLatest() {
    pinLatestObs?.disconnect();
    pinLatestObs = null;
    if (pinLatestUntil != null) {
      clearTimeout(pinLatestUntil);
      pinLatestUntil = null;
    }
  }

  /** Pin the pane to the true end. A day-group <li> is often taller than the pane. */
  function pinTimelineLatest(sc: HTMLElement) {
    writeScrollTop(sc, sc.scrollHeight);
  }

  /** After open-person layout: viewport from the pane; pin; believe the element if they disagree. */
  function syncOpenPersonScroll(sc: HTMLElement) {
    tlViewportHeight = sc.clientHeight || tlViewportHeight;
    const keep = tlScrollTop;
    pinTimelineLatest(sc);
    if (sc.scrollTop + sc.clientHeight < sc.scrollHeight - 4) {
      pinTimelineLatest(sc);
    }
    if (sc.scrollTop <= 4 && keep > (sc.clientHeight || 0)) {
      // Pin missed (layout not ready): keep the end-window so spacerTop stays huge
      // only until watchPinLatest lands — do not collapse to scrollTop 0.
      tlScrollTop = keep;
      return;
    }
    if (sc.scrollTop !== tlScrollTop) tlScrollTop = sc.scrollTop;
  }

  function watchPinLatest(sc: HTMLElement) {
    stopPinLatest();
    syncOpenPersonScroll(sc);
    const ol = sc.querySelector("ol");
    pinLatestObs = new ResizeObserver(() => {
      tlViewportHeight = sc.clientHeight || tlViewportHeight;
      const keep = tlScrollTop;
      writeScrollTop(sc, sc.scrollHeight);
      if (sc.scrollTop <= 4 && keep > (sc.clientHeight || 0)) {
        tlScrollTop = keep;
      }
    });
    pinLatestObs.observe(sc);
    if (ol) pinLatestObs.observe(ol);
    pinLatestUntil = setTimeout(stopPinLatest, 600);
  }

  /** After toReversed, undated rows sit at the top; cursor must be a real sent_at. */
  function oldestSentAt(rows: TimelineRow[]): string | null {
    for (const row of rows) {
      if (row.sent_at) return row.sent_at;
    }
    return null;
  }

  const oldestCursor = $derived(oldestSentAt(timeline));

  const selectedConversation = $derived(
    conversations.find((c) => c.id === selectedConversationId),
  );

  /** Pretty platform labels for chips and the filter toolbar. */
  function platformLabel(platform: string | null | undefined) {
    const p = (platform ?? "").trim().toLowerCase();
    if (p === "whatsapp") return "WhatsApp";
    if (p === "gmail") return "Gmail";
    if (p === "contacts") return "Contacts";
    if (!p) return "";
    return p.charAt(0).toUpperCase() + p.slice(1);
  }

  /** Pretty conversation-kind labels for the kind filter toolbar. */
  function kindLabel(kind: string | null | undefined) {
    const k = (kind ?? "").trim().toLowerCase();
    if (k === "dm") return "DMs";
    if (k === "email_thread") return "Email threads";
    if (k === "group") return "Groups";
    if (!k) return "";
    return k.charAt(0).toUpperCase() + k.slice(1);
  }

  /** Empty / person-name titles → WhatsApp, Gmail, …; keep group names and subjects. */
  function conversationLabel(title: string | null | undefined, platform: string | null | undefined) {
    if (
      !(title ?? "").trim() ||
      (title ?? "").trim().toLowerCase() === personTitle.trim().toLowerCase()
    ) {
      return platformLabel(platform);
    }
    return title;
  }

  async function selectPerson(id: number, append = false, keepConversation = false) {
    if (append && tlLoading) return;
    // Newest-first API page; `before` is the oldest dated row already on screen.
    const before = append ? oldestSentAt(timeline) : null;
    if (append && !before) return;

    if (!append && id !== selectedId) {
      showPersonChrome = false;
      platformFilter = "all";
      kindFilter = "all";
      quotedOpen = {};
    }
    selectedId = id;
    if (!append && !keepConversation) {
      selectedConversationId = null;
    }
    const gen = ++tlGen;
    tlAppending = append;
    tlLoading = true;
    tlError = "";
    stopPinLatest();
    try {
      const show = await api.personShow(id);
      if (gen !== tlGen) return;
      personTitle = show.display_name || `person ${id}`;
      identities = show.identities || [];
      if (!append && !keepConversation) {
        conversations = await api.personConversations({ id, includeGroups });
        if (gen !== tlGen) return;
      }
      const page = await api.personTimeline({
        id,
        includeGroups,
        limit: 80,
        before,
        conversationId: selectedConversationId,
      });
      if (gen !== tlGen) return;
      const pane = document.getElementById("person-timeline");
      const prevHeight = pane?.scrollHeight ?? 0;
      const chrono = page.toReversed();
      if (append) {
        const n = chrono.length;
        const next: Record<number, number> = {};
        for (const [k, v] of Object.entries(rowHeights)) {
          next[Number(k) + n] = v;
        }
        clearPendingMeasures();
        rowHeights = next;
      } else {
        clearPendingMeasures();
        rowHeights = {};
      }
      timeline = append ? chrono.concat(timeline) : chrono;
      tlIndex = append ? tlIndex + chrono.length : Math.max(0, chrono.length - 1);
      if (append) {
        await tick();
        if (gen !== tlGen) return;
        const sc = document.getElementById("person-timeline");
        if (sc) {
          writeScrollTop(sc, sc.scrollTop + (sc.scrollHeight - prevHeight));
        }
      } else {
        // Window from the end before first paint so open-person does not flash the top.
        const sc0 = document.getElementById("person-timeline");
        if (sc0) tlViewportHeight = sc0.clientHeight || tlViewportHeight;
        const estTotal = Math.max(offsetOf(filteredTimeline.length), ESTIMATED_ROW_HEIGHT);
        tlScrollTop = estTotal;
        // Loading line still in the pane makes one rAF land short after wrap.
        tlLoading = false;
        await tick();
        if (gen !== tlGen) return;
        const sc = document.getElementById("person-timeline");
        if (sc) {
          tlViewportHeight = sc.clientHeight || tlViewportHeight;
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              if (gen !== tlGen) return;
              tlViewportHeight = sc.clientHeight || tlViewportHeight;
              const keep = tlScrollTop;
              programmaticScroll = true;
              sc.scrollTop = sc.scrollHeight;
              tlScrollTop = sc.scrollTop;
              programmaticScroll = false;
              if (sc.scrollTop <= 4 && keep > (sc.clientHeight || 0)) {
                tlScrollTop = keep;
              } else if (sc.scrollTop !== tlScrollTop) {
                tlScrollTop = sc.scrollTop;
              }
              watchPinLatest(sc);
            });
          });
        }
      }
    } catch (e) {
      if (gen === tlGen) {
        tlError = friendly(e instanceof Error ? e.message : String(e ?? ""));
        if (!append) timeline = [];
      }
    } finally {
      if (gen === tlGen) {
        tlLoading = false;
        tlAppending = false;
      }
    }
  }

  /**
   * Search hit → People: select person, page the timeline until message_id is
   * loaded (bounded), set tlIndex, scroll virtual window + highlight once.
   * Optional sentAt seeks the first page near the hit (before just after it).
   * Miss after the walk: showErr — never ring an unrelated row as the hit.
   */
  async function openPersonAtMessage(
    personId: number,
    messageId: number,
    sentAt?: string | null,
  ) {
    showPersonChrome = false;
    platformFilter = "all";
    kindFilter = "all";
    quotedOpen = {};
    selectedId = personId;
    selectedConversationId = null;
    const gen = ++tlGen;
    tlAppending = false;
    tlLoading = true;
    tlError = "";
    stopPinLatest();
    try {
      const show = await api.personShow(personId);
      if (gen !== tlGen) return;
      personTitle = show.display_name || `person ${personId}`;
      identities = show.identities || [];
      conversations = await api.personConversations({
        id: personId,
        includeGroups,
      });
      if (gen !== tlGen) return;

      // Newest-first pages; reverse each batch and prepend until hit or cap.
      // Core cursor is exclusive (`m.sent_at < before`); seed just after hit
      // sent_at so the first page can include it instead of walking from newest.
      const pageLimit = 200;
      const maxPages = 80;
      const seekAt = (sentAt ?? "").trim();
      let loaded: TimelineRow[] = [];
      let before: string | null = seekAt ? `${seekAt}~` : null;
      for (let page = 0; page < maxPages; page++) {
        const batch = await api.personTimeline({
          id: personId,
          includeGroups,
          limit: pageLimit,
          before,
          conversationId: null,
        });
        if (gen !== tlGen) return;
        if (batch.length === 0) break;
        const chrono = batch.toReversed();
        loaded = page === 0 ? chrono : chrono.concat(loaded);
        if (loaded.some((r) => r.message_id === messageId)) break;
        const nextBefore = oldestSentAt(loaded);
        if (!nextBefore || batch.length < pageLimit) break;
        before = nextBefore;
      }
      if (gen !== tlGen) return;

      timeline = loaded;
      clearPendingMeasures();
      rowHeights = {};
      const idx = loaded.findIndex((r) => r.message_id === messageId);
      if (idx < 0) {
        tlIndex = -1;
        showErr(
          "Could not find that message on the person timeline (too far back or not in this view).",
        );
        return;
      }
      tlIndex = idx;

      // Estimate scroll so the virtual window covers the target on first paint.
      const hitPos = visibleTlIndices.indexOf(tlIndex);
      const estTop = Math.max(
        0,
        offsetOf(hitPos >= 0 ? hitPos : tlIndex) - ESTIMATED_ROW_HEIGHT * 2,
      );
      tlScrollTop = estTop;
      tlLoading = false;
      await tick();
      if (gen !== tlGen) return;
      ensureTlIndexVisible(tlIndex);
      requestAnimationFrame(() => {
        if (gen !== tlGen) return;
        ensureTlIndexVisible(tlIndex);
      });
    } catch (e) {
      if (gen === tlGen) {
        tlError = friendly(e instanceof Error ? e.message : String(e ?? ""));
        timeline = [];
      }
    } finally {
      if (gen === tlGen) tlLoading = false;
    }
  }

  /** SearchPane hit with person_id: People view + open at that message. */
  async function jumpToMessage(args: {
    personId: number;
    messageId: number;
    conversationKind?: string | null;
    sentAt?: string | null;
  }) {
    view = "people";
    // Group hits need include-groups so group rows can appear.
    if (
      (args.conversationKind ?? "").toLowerCase() === "group" &&
      !includeGroups
    ) {
      includeGroups = true;
    }
    await tick();
    await openPersonAtMessage(args.personId, args.messageId, args.sentAt);
  }

  async function pickConversation(conversationId: number | null) {
    if (!selectedId) return;
    selectedConversationId = conversationId;
    await selectPerson(selectedId, false, true);
  }

  function personLabel(p: { display_name: string; is_self: boolean }) {
    return p.is_self ? `${p.display_name} (self)` : p.display_name;
  }

  function personById(id: number | null): Person | undefined {
    if (id == null) return undefined;
    return people.find((p) => p.id === id);
  }

  const selectedPerson = $derived(personById(selectedId));

  const personInspectorAttr = ["data", "person", "inspector"].join("-");

  function focusPersonInspector() {
    void tick().then(() => {
      (document.querySelector(`[${personInspectorAttr}]`) as HTMLElement | null)?.focus();
    });
  }

  function openMerge() {
    const keep = personById(selectedId);
    if (!keep) {
      err = "select a person first";
      return;
    }
    err = "";
    mergeKeepId = keep.id;
    mergeKeepName = personLabel(keep);
    mergeQuery = "";
    allowSelf = false;
    mergeOpen = true;
  }

  function pickMergeTarget(other: Person) {
    if (mergeKeepId == null || !mergeKeepName) return;
    const keep = mergeKeepId;
    const keepName = mergeKeepName;
    const otherName = personLabel(other);
    mergeOpen = false;
    const extra = other.is_self
      ? `This absorbs the self person into ${keepName}. The self flag is not copied onto the survivor. `
      : "";
    ask(
      `Merge ${otherName} into ${keepName}?`,
      `${extra}Identity links move. Message rows are not rewritten. Names never auto-merge.`,
      async () => {
        const out = await api.merge(keep, other.id, keep);
        await refreshPeople();
        await refreshEvents();
        await selectPerson(out.survivor);
      },
    );
  }

  function doUnlink(id: number) {
    ask(`Unlink identity ${id}?`, "The identity and its messages stay. Only the person link is dropped.", async () => {
      await api.unlink(id);
      if (selectedId) await selectPerson(selectedId);
      await refreshEvents();
    });
  }

  function undoOpLabel(op: string) {
    if (op === "merge_persons") return "Merge";
    if (op === "link") return "Link";
    if (op === "unlink") return "Unlink";
    return op;
  }

  function undoPersonName(e: LinkEvent) {
    if (e.loser_display_name) return e.loser_display_name;
    const ids = [e.person_id, e.keep, e.loser].filter(
      (id): id is number => id != null,
    );
    for (const id of ids) {
      const p = people.find((x) => x.id === id);
      if (p) return p.display_name;
    }
    return undefined;
  }

  function undoRowLabel(e: LinkEvent) {
    const op = undoOpLabel(e.op);
    const name = undoPersonName(e);
    return name ? `${op} ${name}` : op;
  }

  function doUndo(id: number) {
    ask("Undo last link?", "Reverses the last identity graph change. Messages stay put.", async () => {
      await api.undo(id);
      await refreshPeople();
      await refreshEvents();
      if (selectedId) await selectPerson(selectedId);
    });
  }

  async function whenSearchPaneReady(): Promise<HTMLInputElement | null> {
    view = "search";
    for (let i = 0; i < 40; i++) {
      await tick();
      if (booting || opening) continue;
      const qEl = document.getElementById("q");
      if (qEl instanceof HTMLInputElement) return qEl;
    }
    const qEl = document.getElementById("q");
    return qEl instanceof HTMLInputElement ? qEl : null;
  }

  function submitChromeSearch(e: Event) {
    e.preventDefault();
    void whenSearchPaneReady().then((qEl) => {
      if (!qEl) return;
      qEl.focus();
      qEl.form?.requestSubmit();
    });
  }

  function runCommandView(next: "people" | "search" | "review" | "import" | "doctor") {
    commandOpen = false;
    if (next === "search") {
      void whenSearchPaneReady().then((qEl) => qEl?.focus());
      return;
    }
    view = next;
  }

  function runCommandPerson(p: Person) {
    view = "people";
    void selectPerson(p.id);
    commandOpen = false;
  }

  function onKey(e: KeyboardEvent) {
    const t = e.target as HTMLElement | null;
    const digit = e.key >= "1" && e.key <= "5" ? e.key : /^Digit[1-5]$/.test(e.code) ? e.code.slice(5) : "";
    // AltGr is ctrlKey+altKey; do not treat it as ⌘/Ctrl (AZERTY/Turkish-Q type ~#{[ via AltGr+digit).
    const mod = e.metaKey || (e.ctrlKey && !e.altKey);
    const slashKey =
      e.key === "\\" || e.code === "Backslash" || e.code === "IntlBackslash";
    if (commandOpen && e.key === "Escape") {
      e.preventDefault();
      commandOpen = false;
      return;
    }
    if (commandOpen && t?.closest?.("[data-command-palette]")) return;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) {
      // ⌘F / ⌘K / ⌘\ / ⌘1–5 still apply from a field (stop the webview Find / tab accel).
      if (!(mod && (e.key === "f" || e.key === "F" || e.key === "k" || e.key === "K" || slashKey || e.code === "Backslash" || e.code === "IntlBackslash" || digit !== ""))) {
        if (e.key === "Escape") t.blur();
        return;
      }
    }
    if (mod && (e.key === "k" || e.key === "K")) {
      e.preventDefault();
      commandOpen = true;
      return;
    }
    if (mod && (e.key === "f" || e.key === "F")) {
      e.preventDefault();
      void whenSearchPaneReady().then((qEl) => qEl?.focus());
      return;
    }
    if (mod && slashKey) {
      e.preventDefault();
      persistSidebar(!sidebarCollapsed);
      return;
    }
    if (mod && digit !== "") {
      e.preventDefault();
      const tabs = ["people", "search", "review", "import", "doctor"] as const;
      const next = tabs[Number(digit) - 1];
      if (next) view = next;
      return;
    }
    if (e.key === "Escape") {
      if (copyMenu) { closeCopyMenu(); return; }
      if (document.querySelector("[data-context-menu]")) { e.preventDefault(); return; }
      const ae = document.activeElement as HTMLElement | null;
      if (showPersonChrome && ae?.closest?.(`[${personInspectorAttr}]`)) {
        e.preventDefault();
        showPersonChrome = false;
        return;
      }
      view = "people";
      return;
    }
    // Timeline j/k only on People; Search has its own hit list keys.
    if (view !== "people") return;
    if (e.key === "/") {
      e.preventDefault();
      document.getElementById("person-filter")?.focus();
      return;
    }
    const inPeopleList =
      (t?.closest?.("[role='listbox']") || t?.getAttribute?.("role") === "option") &&
      t?.id !== "person-filter" &&
      t?.tagName !== "INPUT";
    if (inPeopleList && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      e.preventDefault();
      const ids = filtered.map((p) => p.id);
      if (!ids.length) return;
      const cur = selectedId != null ? ids.indexOf(selectedId) : -1;
      const next =
        e.key === "ArrowDown"
          ? Math.min(ids.length - 1, Math.max(0, cur) + (cur < 0 ? 0 : 1))
          : Math.max(0, cur < 0 ? 0 : cur - 1);
      if (ids[next] === selectedId) return;
      void selectPerson(ids[next]);
      void tick().then(() => {
        const box = document.querySelector("[role='listbox'][aria-label='People']");
        const opt = box?.querySelector(
          "[role='option'][aria-selected='true']",
        ) as HTMLElement | null;
        opt?.focus();
      });
      return;
    }
    // Walk only rows currently shown (platform / kind filters may hide some).
    const visible = visibleTlIndices;
    if (!visible.length) return;
    let pos = visible.indexOf(tlIndex);
    if (pos < 0) {
      tlIndex = nearestVisibleTlIndex(tlIndex, visible);
      pos = visible.indexOf(tlIndex);
    }
    if (e.key === "j" || (!inPeopleList && e.key === "ArrowDown")) {
      if (pos >= 0 && pos < visible.length - 1) {
        tlIndex = visible[pos + 1];
        ensureTlIndexVisible(tlIndex);
      }
      e.preventDefault();
    }
    if (e.key === "k" || (!inPeopleList && e.key === "ArrowUp")) {
      if (pos > 0) {
        tlIndex = visible[pos - 1];
        ensureTlIndexVisible(tlIndex);
      }
      e.preventDefault();
    }
  }

  onMount(() => {
    userCollapsed = readSidebarPref();
    syncNarrow();
    window.addEventListener("resize", syncNarrow);
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onCopyMenuAway);
    window.addEventListener("pointerup", onTimelinePointerUp);
    let menuGone = false;
    const menuUnlisten: Array<() => void> = [];
    const keepMenu = (unlisten: () => void) => {
      if (menuGone) unlisten();
      else menuUnlisten.push(unlisten);
    };
    void listen("menu-open-archive", () => {
      void openPicker();
    }).then(keepMenu);
    void listen("menu-import", () => {
      view = "import";
    }).then(keepMenu);
    void listen("menu-view", (e) => {
      const next = e.payload;
      if (next === "people") view = "people";
      else if (next === "search") view = "search";
      else if (next === "review") view = "review";
      else if (next === "doctor") view = "doctor";
    }).then(keepMenu);
    void getCurrentWebview()
      .onDragDropEvent((event) => {
        if (event.payload.type !== "drop") return;
        const paths = event.payload.paths ?? [];
        void importDroppedPaths(paths);
      })
      .then(keepMenu);
    (async () => {
      try {
        const remembered = await api.rememberedPath();
        if (remembered) {
          await openPath(remembered);
          return;
        }
      } catch (e) {
        showErr(e);
        setup = true;
      } finally {
        booting = false;
      }
      setup = true;
    })();
    return () => {
      menuGone = true;
      for (const unlisten of menuUnlisten) unlisten();
      window.removeEventListener("resize", syncNarrow);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onCopyMenuAway);
      window.removeEventListener("pointerup", onTimelinePointerUp);
      stopPinLatest();
    };
  });
</script>

{#snippet timelinePaneState()}
  {#if tlLoading}
    {#if !tlAppending}
    <div class="space-y-2 pt-2" aria-hidden="true">
      <Skeleton class="h-4 w-[92%]" />
      <Skeleton class="h-3 w-[68%]" />
      <Skeleton class="h-4 w-[84%]" />
      <Skeleton class="h-3 w-[56%]" />
      <Skeleton class="h-4 w-[76%]" />
    </div>
    {/if}
  {:else if !selectedId}
    <div class="py-6">
      <EmptyState
        title="Select a person"
        body="Click a name on the left. Groups stay hidden until you tick include groups."
        actionLabel="People"
        onAction={() => document.getElementById("person-filter")?.focus()}
      />
    </div>
  {:else if tlError}
    <div class="py-6">
      <div
        class="rounded-md border border-destructive/40 bg-muted/40 px-4 py-6 text-sm"
        data-partial
      >
        <p class="font-medium text-destructive">Error</p>
        <p class="mt-1 text-muted-foreground">{tlError}</p>
        <Button
          size="sm"
          class="mt-3"
          onclick={() => selectedId && selectPerson(selectedId)}>Retry</Button
        >
      </div>
    </div>
  {:else if filteredTimeline.length === 0}
    <div class="py-6">
      <EmptyState
        title="No messages in this view"
        body={timeline.length === 0
          ? "This person may only appear in groups. Tick include groups, or import more sources."
          : "Nothing matches the current platform or kind filter. Try All, or another chip."}
        actionLabel={timeline.length > 0
          ? "Show all"
          : includeGroups
            ? "Import"
            : "Include groups"}
        onAction={() => {
          if (timeline.length > 0) {
            platformFilter = "all";
            kindFilter = "all";
            return;
          }
          if (selectedId && !includeGroups) {
            includeGroups = true;
            selectPerson(selectedId);
            return;
          }
          view = "import";
        }}
      />
    </div>
  {/if}
{/snippet}

<div class="flex h-full flex-col bg-background text-foreground">
  <header
    class="flex items-center justify-end border-b border-border py-2 pl-20 pr-4 text-sm"
    data-tauri-drag-region
  >
    <span class="text-muted-foreground">offline · no account · no HTTP client</span>
  </header>
  {#if !setup && st}
    <nav class="flex flex-wrap items-center gap-1 border-b border-border px-3 py-1 text-sm">
      <Button size="sm" variant={view === "people" ? "default" : "ghost"} onclick={() => (view = "people")}
        >{t("people")}</Button
      >
      <Button size="sm" variant={view === "search" ? "default" : "ghost"} onclick={() => (view = "search")}
        >{t("search")}</Button
      >
      <Button size="sm" variant={view === "review" ? "default" : "ghost"} onclick={() => (view = "review")}
        >{t("review")}{#if st.review_open} ({st.review_open}){/if}</Button
      >
      <Button size="sm" variant={view === "import" ? "default" : "ghost"} onclick={() => (view = "import")}
        >{t("import")}</Button
      >
      <Button size="sm" variant={view === "doctor" ? "default" : "ghost"} onclick={() => (view = "doctor")}
        >{t("doctor")}{#if doctor.length} ({doctor.length}){/if}</Button
      >
      <form
        class="ml-auto min-w-[10rem] max-w-[16rem] flex-1"
        data-chrome-search
        onsubmit={submitChromeSearch}
      >
        <Input
          type="search"
          bind:value={searchQ}
          placeholder={t("searchPlaceholder")}
          aria-label={t("search")}
          autocomplete="off"
          class="h-8"
          disabled={booting || opening}
        />
      </form>
    </nav>
  {/if}

  {#if err}
    <p class="whitespace-pre-wrap bg-destructive/15 px-4 py-2 text-sm text-destructive">{err}</p>
  {/if}

  {#if st && cloudWarning}
    <Card
      class="rounded-none border-x-0 border-t-0 border-warning bg-warning/15 px-4 py-2 text-sm text-warning shadow-none"
      data-cloud-warning
    >
      <p class="font-medium">This archive looks like it sits on iCloud, Dropbox, or Google Drive.</p>
      <p class="mt-0.5">
        The folder is the backup unit. Not encrypted at rest — FileVault is your encryption. Move the
        live folder off cloud sync; see <code class="text-xs">docs/user/backup.md</code>.
      </p>
    </Card>
  {/if}

  {#if booting || opening}
    <main class="flex h-full flex-col items-center justify-center gap-3 p-6">
      <div
        class="h-8 w-8 animate-spin rounded-full border-2 border-muted border-t-foreground motion-reduce:animate-none"
        role="status"
        aria-label={opening ? "Opening archive" : "Opening last archive"}
      ></div>
      <p class="text-sm text-muted-foreground">
        {opening ? "Opening archive…" : "Opening last archive…"}
      </p>
      <p class="text-xs text-muted-foreground">If this hangs, another Interlace or CLI writer may hold the lock.</p>
    </main>
  {:else if setup}
    <main class="mx-auto w-full max-w-lg space-y-4 p-6">
      <h1 class="text-2xl font-semibold tracking-tight">{t("openAnArchive")}</h1>
      <p class="text-muted-foreground">
        Offline archive. No account. No sync. This window never phones home.
      </p>
      <div class="space-y-1.5">
        <Label for="region">Phone region (ISO 3166-1 alpha-2, required)</Label>
        <Input id="region" bind:value={region} maxlength={2} placeholder="TR" />
      </div>
      <div class="space-y-1.5">
        <Label for="name">Your name</Label>
        <Input id="name" bind:value={name} placeholder="optional" />
      </div>
      <div class="space-y-1.5">
        <Label for="emails">Emails (comma-separated)</Label>
        <Input id="emails" bind:value={emails} placeholder="optional" />
      </div>
      <div class="space-y-1.5">
        <Label for="phones">Phones (comma-separated)</Label>
        <Input id="phones" bind:value={phones} placeholder="optional" />
      </div>
      <div class="flex gap-2">
        <Button onclick={createArchive}>{t("createArchive")}</Button>
        <Button variant="outline" onclick={openPicker}>{t("openExisting")}</Button>
      </div>
      <p class="text-sm text-muted-foreground">
        Folder picker only — no URLs. Phone-region has no silent default. The folder is the backup
        unit. Not encrypted at rest; use FileVault.
      </p>
    </main>
  {:else if st && view === "search"}
    <SearchPane
      bind:q={searchQ}
      {people}
      {friendly}
      onError={showErr}
      onToast={showToast}
      onJumpToMessage={jumpToMessage}
    />
  {:else if st && view === "review"}
    <ReviewPane
      onError={showErr}
      onChanged={async () => {
        await applyStatus(await api.status());
      }}
      onGoImport={() => (view = "import")}
    />
  {:else if st && view === "import"}
    <ImportPane
      onError={showErr}
      onToast={showToast}
      onDone={async () => {
        await applyStatus(await api.status());
      }}
    />
  {:else if st && view === "doctor"}
    <DoctorPane
      bind:issues={doctor}
      {friendly}
      onError={showErr}
      onDone={async () => {
        await applyStatus(await api.status());
      }}
      onGoPeople={() => (view = "people")}
    />
  {:else if st}
    <div class="flex min-h-0 min-w-0 flex-1">
      <div
        data-people-sidebar
        data-people-sidebar-collapsed={sidebarCollapsed ? true : undefined}
        aria-busy={peopleLoading}
        class="min-h-0 min-w-0 shrink-0 overflow-x-hidden overflow-y-auto border-r border-border {sidebarCollapsed
          ? 'w-12 p-1'
          : 'w-72 p-4'}"
      >
        <div class="flex {sidebarCollapsed ? 'justify-center' : 'justify-end'}">
          <Button
            variant="ghost"
            size="icon"
            class="size-8 shrink-0"
            data-sidebar-toggle
            aria-expanded={!sidebarCollapsed}
            aria-label={sidebarCollapsed ? t("expandSidebar") : t("collapseSidebar")}
            onclick={() => persistSidebar(!sidebarCollapsed)}
          >
            {#if sidebarCollapsed}
              <PanelLeft class="size-4" />
            {:else}
              <PanelLeftClose class="size-4" />
            {/if}
          </Button>
        </div>
        {#if !sidebarCollapsed}
        <p class="break-all text-xs text-muted-foreground">{st.path}</p>
        <dl class="mt-3 grid min-w-0 grid-cols-[auto_minmax(0,1fr)] gap-x-2 gap-y-1 text-sm">
          <dt class="text-muted-foreground">owner</dt>
          <dd class="min-w-0 truncate">{st.owner_display_name || "—"}</dd>
          <dt class="text-muted-foreground">region</dt>
          <dd class="min-w-0 truncate">{st.default_phone_region || "—"}</dd>
          <dt class="text-muted-foreground">messages</dt>
          <dd class="min-w-0 truncate">{st.messages}</dd>
          <dt class="text-muted-foreground">identities</dt>
          <dd class="min-w-0 truncate">{st.identities}</dd>
          <dt class="text-muted-foreground">persons</dt>
          <dd class="min-w-0 truncate">{st.persons_live}</dd>
          <dt class="text-muted-foreground">review</dt>
          <dd class="min-w-0 truncate">{st.review_open}</dd>
        </dl>
        <p class="mt-2 truncate text-xs text-muted-foreground">
          {st.last_import
            ? `last import id=${st.last_import.id} status=${st.last_import.status}`
            : "no imports yet"}
        </p>
        {#if st.warnings?.length}
          <ul class="mt-2 min-w-0 list-disc pl-4 text-sm text-muted-foreground">
            {#each st.warnings as w}
              <li class="break-words">{w}</li>
            {/each}
          </ul>
        {/if}
        {#if doctor.length}
          <div class="mt-2 min-w-0 rounded-md border border-warning bg-warning/15 p-2 text-sm text-warning">
            <p class="font-medium">Doctor found {doctor.length} issue{doctor.length === 1 ? "" : "s"}</p>
            <ul class="mt-1 min-w-0 list-disc pl-4">
              {#each doctor as d}
                <li class="break-words">{d}</li>
              {/each}
            </ul>
            <p class="mt-1 text-xs">Open the Doctor tab to run integrity, rebuild FTS, or GC CAS in-app.</p>
          </div>
        {/if}
        {/if}
        <div class={sidebarCollapsed ? "sr-only" : "mt-4 min-w-0 space-y-1.5"}>
          <Label for="person-filter">Filter people</Label>
          <Input id="person-filter" type="search" bind:value={filter} placeholder="name" class="min-w-0" />
        </div>
        <ul class="mt-2 min-w-0 space-y-0.5" role="listbox" aria-label="People" aria-busy={peopleLoading}>
          {#each filtered as p}
            <li class="min-w-0" role="presentation">
              <button
                type="button"
                role="option"
                aria-selected={selectedId === p.id}
                tabindex={p.id === peopleTabId ? 0 : -1}
                title={p.display_name}
                aria-label={`${p.display_name}${p.is_self ? " (self)" : ""}${p.last_activity_at ? ` ${humanTime(p.last_activity_at)}` : ""}`}
                class="w-full min-w-0 max-w-full rounded-md text-sm hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring {sidebarCollapsed
                  ? 'flex justify-center px-0 py-1'
                  : 'px-2 py-1.5 text-left'} {selectedId === p.id
                  ? 'bg-accent'
                  : ''} {p.is_self ? 'font-semibold' : ''}"
                onclick={() => selectPerson(p.id)}
              >
                {#if sidebarCollapsed}
                  <span class="flex size-8 items-center justify-center rounded-md text-sm font-medium" aria-hidden="true">
                    {#if p.display_name.charAt(0)}
                      {p.display_name.charAt(0)}
                    {:else}
                      <User class="size-4" />
                    {/if}
                  </span>
                {:else}
                  <span class="block truncate">{p.is_self ? `${p.display_name} (self)` : p.display_name}</span>
                  {#if p.last_activity_at || p.preview}
                    <span class="mt-0.5 block truncate text-xs font-normal text-muted-foreground">
                      {humanTime(p.last_activity_at)}{p.last_activity_at && p.preview ? " · " : ""}{p.preview ?? ""}
                    </span>
                  {/if}
                {/if}
              </button>
            </li>
          {/each}
        </ul>
        {#if !sidebarCollapsed}
        {#if peopleLoading}
          <div class="mt-3 min-w-0 space-y-2" aria-hidden="true">
            <Skeleton class="h-4 w-[88%]" />
            <Skeleton class="h-3 w-[64%]" />
            <Skeleton class="h-4 w-[80%]" />
            <Skeleton class="h-3 w-[52%]" />
            <Skeleton class="h-4 w-[72%]" />
            <Skeleton class="h-3 w-[58%]" />
          </div>
        {:else if people.length === 0}
          <div class="mt-3 min-w-0">
            <EmptyState
              title="No people yet"
              body="Import a WhatsApp ZIP or Takeout from the Import tab. Name-only chats become people after import."
              actionLabel="Import"
              onAction={() => (view = "import")}
            />
          </div>
        {:else if filtered.length === 0}
          <div class="mt-3 min-w-0">
            <EmptyState
              title="No match"
              body="Clear the filter or try another spelling."
              actionLabel="Clear filter"
              onAction={() => (filter = "")}
            />
          </div>
        {/if}
        {#if undoableEvents.length > 0}
        <ul class="mt-3 min-w-0 space-y-1 text-xs">
          {#each undoableEvents as e}
            <li class="flex min-w-0 items-center justify-between gap-2">
              <span class="min-w-0 truncate">{undoRowLabel(e)}</span>
              <Button variant="outline" size="sm" class="shrink-0" tabindex="-1" onclick={() => doUndo(e.id)}>
                undo
              </Button>
            </li>
          {/each}
        </ul>
        {/if}
        <Button variant="outline" size="sm" class="mt-4 max-w-full" tabindex="-1" onclick={openPicker}>
          Open other archive…
        </Button>
        {/if}
      </div>
      <div class="flex min-h-0 min-w-0 flex-1 flex-col">
        <div class="flex min-h-0 min-w-0 flex-1">
          <div class="flex min-h-0 min-w-0 flex-1 flex-col">
        <div class="relative z-20 shrink-0 bg-background px-4 pt-4">
        <div class="mb-3 flex items-baseline justify-between gap-3">
          <h1 class="text-xl font-semibold tracking-tight">
            <button
              type="button"
              class="text-left focus-visible:ring-2 focus-visible:ring-ring"
              onclick={() => (
                (showPersonChrome = !showPersonChrome),
                showPersonChrome && focusPersonInspector()
              )}
            >
              {personTitle}
            </button>
          </h1>
          {#if false}
            {#if selectedId && conversations.length > 1}
              <details data-conversation-switcher class="relative z-20 min-w-0 max-w-[16rem]">
                <summary
                  class="cursor-pointer truncate rounded-md border border-border px-2 py-1 text-sm focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {#if selectedConversationId === null}
                    All
                  {:else}
                    {conversationLabel(selectedConversation?.title, selectedConversation?.platform)}
                  {/if}
                </summary>
                <ul
                  class="absolute right-0 z-10 mt-1 min-w-[14rem] space-y-0.5 rounded-md border border-border bg-background p-1 shadow-md"
                >
                  <li>
                    <button
                      type="button"
                      class="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring {selectedConversationId ===
                      null
                        ? 'bg-accent'
                        : ''}"
                      onclick={() => pickConversation(null)}
                    >
                      All
                    </button>
                  </li>
                  {#each conversations as conv}
                    <li>
                      <button
                        type="button"
                        class="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring {selectedConversationId ===
                        conv.id
                          ? 'bg-accent'
                          : ''}"
                        onclick={() => pickConversation(conv.id)}
                      >
                        <span>{conversationLabel(conv.title, conv.platform)}</span>
                        <span class="mt-0.5 block truncate text-xs font-normal text-muted-foreground">
                          {conv.platform}{conv.last_at ? ` · ${conv.last_at}` : ""}
                        </span>
                      </button>
                    </li>
                  {/each}
                </ul>
              </details>
            {/if}
          {/if}
        </div>
        {#if selectedId && (availablePlatforms.length > 0 || availableKinds.length > 0)}
          <div
            class="timeline-filters mb-4 space-y-2.5 rounded-lg border border-border bg-muted/40 px-3 py-2.5"
            data-timeline-filters
          >
            {#if availablePlatforms.length > 0}
              <div
                data-platform-filter
                class="platform-filter flex flex-wrap items-center gap-x-2 gap-y-1.5"
                role="toolbar"
                aria-label="Filter by platform"
              >
                <span class="filter-section-label shrink-0 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground"
                  >Platform</span
                >
                <div class="flex min-w-0 flex-wrap items-center gap-1.5">
                  <button
                    type="button"
                    class="filter-chip rounded-full border px-2.5 py-0.5 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring {platformFilter ===
                    'all'
                      ? 'filter-chip-active border-border bg-background font-medium text-foreground shadow-sm'
                      : 'border-transparent bg-transparent text-muted-foreground hover:bg-background/70 hover:text-foreground'}"
                    onclick={() => (platformFilter = "all")}
                  >
                    All
                  </button>
                  {#each availablePlatforms as p}
                    <button
                      type="button"
                      class="filter-chip rounded-full border px-2.5 py-0.5 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring {platformFilter ===
                      p
                        ? 'filter-chip-active border-border bg-background font-medium text-foreground shadow-sm'
                        : 'border-transparent bg-transparent text-muted-foreground hover:bg-background/70 hover:text-foreground'}"
                      onclick={() => (platformFilter = p)}
                    >
                      {platformLabel(p)}
                    </button>
                  {/each}
                </div>
              </div>
            {/if}
            {#if availablePlatforms.length > 0 && availableKinds.length > 0}
              <Separator />
            {/if}
            {#if availableKinds.length > 0}
              <div
                data-kind-filter
                class="kind-filter flex flex-wrap items-center gap-x-2 gap-y-1.5"
                role="toolbar"
                aria-label="Filter by kind"
              >
                <span class="filter-section-label shrink-0 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground"
                  >Kind</span
                >
                <div class="flex min-w-0 flex-wrap items-center gap-1.5">
                  <button
                    type="button"
                    class="filter-chip rounded-full border px-2.5 py-0.5 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring {kindFilter ===
                    'all'
                      ? 'filter-chip-active border-border bg-background font-medium text-foreground shadow-sm'
                      : 'border-transparent bg-transparent text-muted-foreground hover:bg-background/70 hover:text-foreground'}"
                    onclick={() => (kindFilter = "all")}
                  >
                    All
                  </button>
                  {#each availableKinds as k}
                    <button
                      type="button"
                      class="filter-chip rounded-full border px-2.5 py-0.5 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring {kindFilter ===
                      k
                        ? 'filter-chip-active border-border bg-background font-medium text-foreground shadow-sm'
                        : 'border-transparent bg-transparent text-muted-foreground hover:bg-background/70 hover:text-foreground'}"
                      onclick={() => (kindFilter = k)}
                    >
                      {kindLabel(k)}
                    </button>
                  {/each}
                </div>
              </div>
            {/if}
          </div>
        {/if}
        </div>
        <ScrollArea
          id="person-timeline"
          class="min-h-0 min-w-0 flex-1 px-4 pb-8"
          aria-busy={tlLoading}
          onscroll={onTimelineScroll}
          onwheel={onTimelineWheel}
          onpointerdown={onTimelinePointerDown}
        >
        {@render timelinePaneState()}
        {#if timeline.length && oldestCursor && filteredTimeline.length > 0}
          <Button
            variant="outline"
            size="sm"
            class="mb-4 mt-4"
            data-load-older
            disabled={tlLoading}
            onclick={() => !tlLoading && selectedId && selectPerson(selectedId, true)}
            >Load older</Button
          >
        {/if}
        <ol class="min-w-0">
          {#if spacerTop > 0}
            <li class="timeline-spacer-top pointer-events-none" style="height: {spacerTop}px" aria-hidden="true"></li>
          {/if}
          {#each windowedDayGroups as group}
            <li class="day-group min-w-0">
              {#if group.rows[0]?.row.sent_at && localDay(group.rows[0].row.sent_at, group.rows[0].row.platform)}
                <h3 class="day-heading mb-2 text-center text-xs font-medium text-muted-foreground">
                  {group.label}
                </h3>
              {/if}
              <div>
                {#each group.rows as item}
                  <div class="flex min-w-0 pb-2" data-tl-index={item.index} use:measureTlRow={item.index}>
                    <article
                      class="flex min-w-0 max-w-[94%] cursor-pointer flex-col gap-2 rounded-2xl px-3 py-2 text-left focus-visible:ring-2 focus-visible:ring-ring {item.index ===
                      tlIndex
                        ? 'ring-2 ring-ring'
                        : ''}"
                      class:bubble-me={item.row.from_me}
                      class:bubble-them={!item.row.from_me}
                      class:ml-auto={item.row.from_me}
                      data-from-me={item.row.from_me}
                      data-grouped={isGroupedFollower(item.index) || undefined}
                      tabindex="0"
                      aria-label={`${utcTime(item.row.sent_at, item.row.platform)} ${displayBody(item.row.body_text || item.row.subject || "").slice(0, 80)}`}
                      onclick={() => (tlIndex = item.index)}
                      oncontextmenu={(e) => openCopyMenu(e, item.row)}
                    >
                      {#if !isGroupedFollower(item.index)}
                      <p
                        class="caption flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground"
                        data-bubble-meta
                      >
                        <time>{utcTime(item.row.sent_at, item.row.platform)}</time>
                        <Badge
                          variant="outline"
                          class="platform-chip rounded-full border-border/80 bg-background/60 px-1.5 py-px text-[0.65rem] font-medium leading-none text-muted-foreground"
                          data-platform-chip
                          >{platformLabel(item.row.platform)}</Badge
                        >
                        {#if isMailRow(item.row) && item.row.from_me}
                          <span class="text-xs text-muted-foreground">You</span>
                        {/if}
                      </p>
                      {/if}
                      <div data-bubble-body>
                      {#if isMailRow(item.row)}
                        {#if (item.row.subject ?? "").trim()}
                          <p class="mail-subject text-sm font-medium text-foreground">
                            {item.row.subject}
                          </p>
                        {/if}
                        {@const parts = splitQuotedBody(item.row.body_text || "")}
                        {#if parts.main || !parts.quoted}
                          <p class="whitespace-pre-wrap break-words text-sm leading-normal text-foreground">
                            <LinkifyBody text={displayBody(parts.main)} {splitUrls} {openUrl} />
                          </p>
                        {/if}
                        {#if parts.quoted}
                          {#if quotedOpen[item.row.message_id]}
                            <p
                              class="mt-1 whitespace-pre-wrap break-words text-sm leading-normal text-muted-foreground"
                            >
                              <LinkifyBody text={displayBody(parts.quoted)} {splitUrls} {openUrl} />
                            </p>
                            <button
                              type="button"
                              class="mt-1 text-xs text-muted-foreground underline focus-visible:ring-2 focus-visible:ring-ring"
                              data-show-quoted
                              onclick={(e) => toggleQuoted(item.row.message_id, e)}
                              >Hide quoted</button
                            >
                          {:else}
                            <button
                              type="button"
                              class="mt-1 text-xs text-muted-foreground underline focus-visible:ring-2 focus-visible:ring-ring"
                              data-show-quoted
                              onclick={(e) => toggleQuoted(item.row.message_id, e)}
                              >Show quoted</button
                            >
                          {/if}
                        {/if}
                      {:else}
                        <p class="whitespace-pre-wrap break-words text-sm leading-normal text-foreground">
                          <LinkifyBody
                            text={displayBody(item.row.body_text || item.row.subject || "")}
                            {splitUrls}
                            {openUrl}
                          />
                        </p>
                      {/if}
                      </div>
                      <CasAttach data-bubble-attach flush={true} items={item.row.attachments || []} {showToast} />
                    </article>
                  </div>
                {/each}
              </div>
            </li>
          {/each}
          {#if spacerBottom > 0}
            <li class="timeline-spacer-bottom pointer-events-none" style="height: {spacerBottom}px" aria-hidden="true"></li>
          {/if}
        </ol>
        <div id="timeline-end"></div>
        </ScrollArea>
          </div>
          {#if showPersonChrome}
            <aside
              data-person-inspector
              tabindex="-1"
              class="flex w-72 shrink-0 flex-col gap-3 overflow-y-auto border-l border-border p-4 text-sm"
              aria-label={t("inspector")}
              transition:fly={{ x: 16, duration: chromeMotionMs() }}
            >
              <p class="font-medium">{personTitle}</p>
              <p class="text-xs text-muted-foreground">
                {t("lastActivity")}
                {humanTime(selectedPerson?.last_activity_at)}
              </p>
              <div class="flex flex-col gap-2">
                <Button variant="outline" size="sm" disabled={!personById(selectedId)} onclick={openMerge}
                  >Merge…</Button
                >
                <label class="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    class="focus-visible:ring-2 focus-visible:ring-ring"
                    bind:checked={includeGroups}
                    onchange={() => selectedId && selectPerson(selectedId)}
                  />
                  include groups
                </label>
              </div>
              <p class="text-xs font-medium">{t("identities")}</p>
              <ul class="space-y-1 text-sm text-muted-foreground">
                {#each identities as ident}
                  <li class="flex items-center justify-between gap-2">
                    <span>{ident.kind} {ident.value || ident.display_name || ""}</span>
                    <Button variant="outline" size="sm" onclick={() => doUnlink(ident.id)}>unlink</Button>
                  </li>
                {/each}
              </ul>
            </aside>
          {/if}
        </div>
        <p class="shrink-0 bg-background px-4 pb-4 pt-2 text-xs text-muted-foreground">
          Bodies are text only. Day headings follow the Mac timezone. <kbd class="rounded border border-border px-1">j</kbd>/<kbd
            class="rounded border border-border px-1">k</kbd
          >
          move.
          <kbd class="rounded border border-border px-1">/</kbd> filters people.
        </p>
      </div>
    </div>
  {/if}
</div>

{#if copyMenu}
  <div
    class="fixed z-[80] min-w-32 rounded-md border border-border bg-background py-1 shadow-md"
    style="left: {copyMenu.x}px; top: {copyMenu.y}px"
    data-copy-menu
    data-context-menu
    role="menu"
  >
    <button
      type="button"
      class="block w-full px-3 py-1.5 text-left text-sm hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
      role="menuitem"
      onclick={copyText}>{t("copyText")}</button
    >
  </div>
{/if}

<Dialog.Root bind:open={mergeOpen}>
  <Dialog.Content>
    <Dialog.Header>
      <Dialog.Title>Merge into {mergeKeepName}</Dialog.Title>
      <Dialog.Description>
        Pick a person by name. {mergeKeepName} is kept. Names never auto-merge.
      </Dialog.Description>
    </Dialog.Header>
    <div class="space-y-1.5">
      <Label for="merge-query">Search</Label>
      <Input
        id="merge-query"
        type="search"
        bind:value={mergeQuery}
        placeholder="name"
      />
    </div>
    <label class="flex items-center gap-2 text-sm">
      <input type="checkbox" class="focus-visible:ring-2 focus-visible:ring-ring" bind:checked={allowSelf} />
      Allow absorbing self into this person
    </label>
    {#if mergeList.length === 0}
      <EmptyState
        title="No match"
        body="Try another spelling, or tick Allow absorbing self into this person."
        actionLabel="Clear filter"
        onAction={() => (mergeQuery = "")}
      />
    {:else}
      <ul class="max-h-64 space-y-0.5 overflow-y-auto">
        {#each mergeList as p}
          <li>
            <button
              type="button"
              class="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring {p.is_self
                ? 'font-semibold'
                : ''}"
              onclick={() => pickMergeTarget(p)}
            >
              <span>{personLabel(p)}</span>
              {#if p.last_activity_at || p.preview}
                <span class="mt-0.5 block truncate text-xs font-normal text-muted-foreground">
                  {humanTime(p.last_activity_at)}{p.last_activity_at && p.preview ? " · " : ""}{p.preview ?? ""}
                </span>
              {/if}
            </button>
          </li>
        {/each}
      </ul>
    {/if}
    <Dialog.Footer>
      <Button variant="outline" onclick={() => (mergeOpen = false)}>Cancel</Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>

{#if toasts.length}
  <div class="pointer-events-none fixed bottom-4 right-4 z-[90] flex flex-col items-end gap-2">
    {#each toasts as item (item.id)}
      <div class="pointer-events-auto">
        <Toast message={item.message} />
      </div>
    {/each}
  </div>
{/if}

<ConfirmDialog
  bind:open={confirmOpen}
  title={confirmTitle}
  description={confirmDesc}
  onconfirm={async () => {
    if (confirmRun) await confirmRun();
  }}
  onerror={showErr}
/>

{#if commandOpen}
  <CommandPalette
    {people}
    {personLabel}
    onView={runCommandView}
    onPerson={runCommandPerson}
    onClose={() => (commandOpen = false)}
  />
{/if}
