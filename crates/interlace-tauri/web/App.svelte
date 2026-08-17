<script lang="ts">
  import { onMount, tick } from "svelte";
  import { listen } from "@tauri-apps/api/event";
  import { getCurrentWebview } from "@tauri-apps/api/webview";
  import { getCurrentWindow } from "@tauri-apps/api/window";
  import { api, type Identity, type LinkEvent, type Person, type PersonConversation, type Status, type TimelineRow } from "./lib/api";
  import { mergeTargets } from "./lib/utils";
  import { humanTime } from "./lib/formatTime";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Card } from "$lib/components/ui/card/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Label } from "$lib/components/ui/label/index.js";
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import { Separator } from "$lib/components/ui/separator/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import ConfirmDialog from "$lib/ConfirmDialog.svelte";
  import SearchPane from "$lib/SearchPane.svelte";
  import ReviewPane from "$lib/ReviewPane.svelte";
  import ImportPane from "$lib/ImportPane.svelte";
  import DoctorPane from "$lib/DoctorPane.svelte";
  import EmptyState from "$lib/EmptyState.svelte";
  import CasAttach from "$lib/CasAttach.svelte";
  import { t } from "$lib/i18n";

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

  let confirmOpen = $state(false);
  let confirmTitle = $state("");
  let confirmDesc = $state("");
  let confirmRun = $state<(() => Promise<void>) | null>(null);
  let view = $state<"people" | "search" | "review" | "import" | "doctor">("people");
  let booting = $state(true);
  let opening = $state(false);
  let tlLoading = $state(false);
  let peopleLoading = $state(true);
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

  const SANDBOX_DENIED =
    "macOS blocked that folder. Use Open existing\u2026 once so Interlace can remember it.";

  function friendly(raw: string): string {
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
        showErr(new Error("Drop a local ZIP or mbox — URLs are not imported."));
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

  let copyMenu = $state<{ x: number; y: number; body_text: string } | null>(null);

  function openCopyMenu(e: MouseEvent, row: TimelineRow) {
    e.preventDefault();
    copyMenu = { x: e.clientX, y: e.clientY, body_text: row.body_text || row.subject || "" };
  }

  function closeCopyMenu() {
    copyMenu = null;
  }

  async function copyText() {
    if (!copyMenu) return;
    const text = displayBody(copyMenu.body_text);
    copyMenu = null;
    try {
      await navigator.clipboard.writeText(text);
    } catch (e) {
      showErr(e);
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

  /** UTC calendar day key (`YYYY-MM-DD`) from RFC3339 `sent_at`. Empty if missing. */
  function utcDay(iso: string | null | undefined): string {
    if (!iso || iso.length < 10) return "";
    return iso.slice(0, 10);
  }

  /** UTC day heading as day/month/year. Empty if `sent_at` is missing. */
  function utcDayLabel(iso: string | null | undefined): string {
    const key = utcDay(iso);
    if (!key) return "";
    const [y, m, d] = key.split("-");
    if (!y || !m || !d) return "";
    return `${d}/${m}/${y}`;
  }

  /** UTC hour:minute from RFC3339 `sent_at`. Empty if missing. */
  function utcTime(iso: string | null | undefined): string {
    if (!iso) return "";
    const t = iso.indexOf("T");
    if (t < 0 || iso.length < t + 6) return "";
    return iso.slice(t + 1, t + 6);
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

  /**
   * #120: window the person timeline — only visible + overscan rows in the DOM.
   * Fixed estimate is enough for scrollability; dogfood measures 10k.
   */
  const ESTIMATED_ROW_HEIGHT = 88;
  const OVERSCAN = 15;
  let tlScrollTop = $state(0);
  let tlViewportHeight = $state(480);

  function onTimelineScroll(e: Event) {
    const el = e.currentTarget as HTMLElement | null;
    if (!el) return;
    tlScrollTop = el.scrollTop;
    tlViewportHeight = el.clientHeight || tlViewportHeight;
  }

  /** Visible filtered-row index range (inclusive start, exclusive end) + overscan. */
  const visibleRange = $derived.by(() => {
    const total = filteredTimeline.length;
    if (total === 0) return { startIndex: 0, endIndex: 0 };
    const vh = Math.max(tlViewportHeight, 200);
    const windowRows = Math.ceil(vh / ESTIMATED_ROW_HEIGHT) + OVERSCAN * 2;
    let startIndex = Math.max(
      0,
      Math.floor(tlScrollTop / ESTIMATED_ROW_HEIGHT) - OVERSCAN,
    );
    let endIndex = Math.min(
      total,
      Math.ceil((tlScrollTop + vh) / ESTIMATED_ROW_HEIGHT) + OVERSCAN,
    );
    // Filter shrink or oversize scrollTop: keep a window on the real list.
    if (startIndex >= total) {
      startIndex = Math.max(0, total - windowRows);
      endIndex = total;
    } else if (endIndex <= startIndex) {
      endIndex = Math.min(total, startIndex + 1);
    }
    return { startIndex, endIndex };
  });

  const spacerTop = $derived(visibleRange.startIndex * ESTIMATED_ROW_HEIGHT);
  const spacerBottom = $derived(
    Math.max(0, (filteredTimeline.length - visibleRange.endIndex) * ESTIMATED_ROW_HEIGHT),
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
      const key = utcDay(row.sent_at);
      // i === 0 starts a group so sticky day heading stays when the day began above the window.
      const dayChanged = i === 0 || key !== utcDay(rows[i - 1]?.row.sent_at);
      const last = groups[groups.length - 1];
      if (!last || dayChanged) {
        groups.push({ key, label: key ? utcDayLabel(row.sent_at) : "", rows: [{ row, index }] });
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
    const rowTop = pos * ESTIMATED_ROW_HEIGHT;
    const rowBottom = rowTop + ESTIMATED_ROW_HEIGHT;
    const viewTop = sc.scrollTop;
    const viewBottom = viewTop + sc.clientHeight;
    if (rowTop < viewTop) {
      sc.scrollTop = Math.max(0, rowTop - ESTIMATED_ROW_HEIGHT);
    } else if (rowBottom > viewBottom) {
      sc.scrollTop = rowBottom - sc.clientHeight + ESTIMATED_ROW_HEIGHT;
    }
    tlScrollTop = sc.scrollTop;
    tlViewportHeight = sc.clientHeight || tlViewportHeight;
  }

  function ask(title: string, description: string, run: () => Promise<void>) {
    confirmTitle = title;
    confirmDesc = description;
    confirmRun = run;
    confirmOpen = true;
  }

  async function refreshPeople() {
    peopleLoading = true;
    try {
      people = await api.people();
    } finally {
      peopleLoading = false;
    }
  }

  async function refreshEvents() {
    events = await api.linkEvents();
  }

  async function applyStatus(next: Status) {
    st = next;
    setup = false;
    await refreshPeople();
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
    sc.scrollTop = sc.scrollHeight;
    tlScrollTop = sc.scrollTop;
    tlViewportHeight = sc.clientHeight || tlViewportHeight;
  }

  function watchPinLatest(sc: HTMLElement) {
    stopPinLatest();
    pinTimelineLatest(sc);
    const ol = sc.querySelector("ol");
    pinLatestObs = new ResizeObserver(() => {
      sc.scrollTop = sc.scrollHeight;
      tlScrollTop = sc.scrollTop;
      tlViewportHeight = sc.clientHeight || tlViewportHeight;
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
    tlLoading = true;
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
      timeline = append ? chrono.concat(timeline) : chrono;
      tlIndex = append ? tlIndex + chrono.length : Math.max(0, chrono.length - 1);
      if (append) {
        await tick();
        if (gen !== tlGen) return;
        const sc = document.getElementById("person-timeline");
        if (sc) {
          sc.scrollTop += sc.scrollHeight - prevHeight;
          tlScrollTop = sc.scrollTop;
          tlViewportHeight = sc.clientHeight || tlViewportHeight;
        }
      } else {
        // Window from the end before first paint so open-person does not flash the top.
        const estTotal = Math.max(chrono.length, 1) * ESTIMATED_ROW_HEIGHT;
        tlScrollTop = estTotal;
        // Loading line still in the pane makes one rAF land short after wrap.
        tlLoading = false;
        await tick();
        if (gen !== tlGen) return;
        const sc = document.getElementById("person-timeline");
        if (sc) {
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              if (gen !== tlGen) return;
              sc.scrollTop = sc.scrollHeight;
              tlScrollTop = sc.scrollTop;
              tlViewportHeight = sc.clientHeight || tlViewportHeight;
              watchPinLatest(sc);
            });
          });
        }
      }
    } catch (e) {
      if (gen === tlGen) showErr(e);
    } finally {
      if (gen === tlGen) tlLoading = false;
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
    tlLoading = true;
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
      const estTop = Math.max(0, tlIndex * ESTIMATED_ROW_HEIGHT - ESTIMATED_ROW_HEIGHT * 2);
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
      if (gen === tlGen) showErr(e);
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

  function doUndo(id: number, op: string) {
    ask(`Undo event ${id} (${op})?`, "Reverses the last identity graph change. Messages stay put.", async () => {
      await api.undo(id);
      await refreshPeople();
      await refreshEvents();
      if (selectedId) await selectPerson(selectedId);
    });
  }

  function onKey(e: KeyboardEvent) {
    const t = e.target as HTMLElement | null;
    const digit = e.key >= "1" && e.key <= "5" ? e.key : /^Digit[1-5]$/.test(e.code) ? e.code.slice(5) : "";
    // AltGr is ctrlKey+altKey; do not treat it as ⌘/Ctrl (AZERTY/Turkish-Q type ~#{[ via AltGr+digit).
    const mod = e.metaKey || (e.ctrlKey && !e.altKey);
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) {
      // ⌘F / ⌘1–5 still apply from a field (stop the webview Find / tab accel).
      if (!(mod && (e.key === "f" || e.key === "F" || digit !== ""))) {
        if (e.key === "Escape") t.blur();
        return;
      }
    }
    if (mod && (e.key === "f" || e.key === "F")) {
      e.preventDefault();
      if (view === "people") {
        document.getElementById("person-filter")?.focus();
      } else {
        view = "search";
        void tick().then(() => document.getElementById("q")?.focus());
      }
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
      if (copyMenu) {
        closeCopyMenu();
        return;
      }
      if (document.querySelector("[data-context-menu]")) {
        e.preventDefault();
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
    // Walk only rows currently shown (platform / kind filters may hide some).
    const visible = visibleTlIndices;
    if (!visible.length) return;
    let pos = visible.indexOf(tlIndex);
    if (pos < 0) {
      tlIndex = nearestVisibleTlIndex(tlIndex, visible);
      pos = visible.indexOf(tlIndex);
    }
    if (e.key === "j" || e.key === "ArrowDown") {
      if (pos >= 0 && pos < visible.length - 1) {
        tlIndex = visible[pos + 1];
        ensureTlIndexVisible(tlIndex);
      }
      e.preventDefault();
    }
    if (e.key === "k" || e.key === "ArrowUp") {
      if (pos > 0) {
        tlIndex = visible[pos - 1];
        ensureTlIndexVisible(tlIndex);
      }
      e.preventDefault();
    }
  }

  onMount(() => {
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onCopyMenuAway);
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
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onCopyMenuAway);
      stopPinLatest();
    };
  });
</script>

<div class="flex h-full flex-col bg-background text-foreground">
  <header class="flex items-center justify-between border-b border-border px-4 py-2 text-sm">
    <strong>Interlace</strong>
    <span class="text-muted-foreground">offline · no account · no HTTP client</span>
  </header>
  {#if !setup && st}
    <nav class="flex flex-wrap gap-1 border-b border-border px-3 py-1 text-sm">
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
    </nav>
  {/if}

  {#if err}
    <p class="whitespace-pre-wrap bg-destructive/15 px-4 py-2 text-sm text-destructive">{err}</p>
  {/if}

  {#if st && cloudWarning}
    <Card
      class="rounded-none border-x-0 border-t-0 bg-muted px-4 py-2 text-sm text-muted-foreground shadow-none"
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
    <SearchPane {people} onError={showErr} onJumpToMessage={jumpToMessage} />
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
      onDone={async () => {
        await applyStatus(await api.status());
      }}
    />
  {:else if st && view === "doctor"}
    <DoctorPane
      bind:issues={doctor}
      onError={showErr}
      onDone={async () => {
        await applyStatus(await api.status());
      }}
      onGoPeople={() => (view = "people")}
    />
  {:else if st}
    <div class="grid min-h-0 min-w-0 flex-1 grid-cols-[minmax(0,18rem)_minmax(0,1fr)]">
      <div
        class="min-h-0 min-w-0 overflow-x-hidden overflow-y-auto border-r border-border p-4"
        data-people-sidebar
      >
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
          <div class="mt-2 min-w-0 rounded-md border border-destructive/40 bg-muted p-2 text-sm text-destructive">
            <p class="font-medium">Doctor found {doctor.length} issue{doctor.length === 1 ? "" : "s"}</p>
            <ul class="mt-1 min-w-0 list-disc pl-4">
              {#each doctor as d}
                <li class="break-words">{d}</li>
              {/each}
            </ul>
            <p class="mt-1 text-xs">Open the Doctor tab to run integrity, rebuild FTS, or GC CAS in-app.</p>
          </div>
        {/if}
        <div class="mt-4 min-w-0 space-y-1.5">
          <Label for="person-filter">Filter people</Label>
          <Input id="person-filter" type="search" bind:value={filter} placeholder="name" class="min-w-0" />
        </div>
        <ul class="mt-2 min-w-0 space-y-0.5" role="listbox" aria-label="People">
          {#each filtered as p}
            <li class="min-w-0" role="presentation">
              <button
                type="button"
                role="option"
                aria-selected={selectedId === p.id}
                aria-label={`${p.display_name}${p.is_self ? " (self)" : ""}${p.last_activity_at ? ` ${humanTime(p.last_activity_at)}` : ""}`}
                class="w-full min-w-0 max-w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring {selectedId ===
                p.id
                  ? 'bg-accent'
                  : ''} {p.is_self ? 'font-semibold' : ''}"
                onclick={() => selectPerson(p.id)}
              >
                <span class="block truncate">{p.is_self ? `${p.display_name} (self)` : p.display_name}</span>
                {#if p.last_activity_at || p.preview}
                  <span class="mt-0.5 block truncate text-xs font-normal text-muted-foreground">
                    {humanTime(p.last_activity_at)}{p.last_activity_at && p.preview ? " · " : ""}{p.preview ?? ""}
                  </span>
                {/if}
              </button>
            </li>
          {/each}
        </ul>
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
        <ul class="mt-3 min-w-0 space-y-1 text-xs">
          {#each events as e}
            <li class="flex min-w-0 items-center justify-between gap-2">
              <span class="min-w-0 truncate">#{e.id} {e.op}</span>
              <Button variant="outline" size="sm" class="shrink-0" onclick={() => doUndo(e.id, e.op)}>
                undo
              </Button>
            </li>
          {/each}
        </ul>
        <Button variant="outline" size="sm" class="mt-4 max-w-full" onclick={openPicker}>
          Open other archive…
        </Button>
      </div>
      <div class="flex min-h-0 min-w-0 flex-col">
        <div class="relative z-20 shrink-0 bg-background px-4 pt-4">
        <div class="mb-3 flex items-baseline justify-between gap-3">
          <h1 class="text-xl font-semibold tracking-tight">
            <button
              type="button"
              class="text-left"
              onclick={() => (showPersonChrome = !showPersonChrome)}
            >
              {personTitle}
            </button>
          </h1>
          {#if false}
            {#if selectedId && conversations.length > 1}
              <details data-conversation-switcher class="relative z-20 min-w-0 max-w-[16rem]">
                <summary
                  class="cursor-pointer truncate rounded-md border border-border px-2 py-1 text-sm"
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
                      class="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent {selectedConversationId ===
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
                        class="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent {selectedConversationId ===
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
                    class="filter-chip rounded-full border px-2.5 py-0.5 text-xs transition-colors {platformFilter ===
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
                      class="filter-chip rounded-full border px-2.5 py-0.5 text-xs transition-colors {platformFilter ===
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
                    class="filter-chip rounded-full border px-2.5 py-0.5 text-xs transition-colors {kindFilter ===
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
                      class="filter-chip rounded-full border px-2.5 py-0.5 text-xs transition-colors {kindFilter ===
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
        {#if showPersonChrome}
          <div class="mb-3 flex items-center gap-3">
            <Button variant="outline" size="sm" disabled={!personById(selectedId)} onclick={openMerge}
              >Merge…</Button
            >
            <label class="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                bind:checked={includeGroups}
                onchange={() => selectedId && selectPerson(selectedId)}
              />
              include groups
            </label>
          </div>
          <ul class="mb-3 space-y-1 text-sm text-muted-foreground">
            {#each identities as ident}
              <li class="flex items-center justify-between gap-2">
                <span>{ident.platform} {ident.kind} {ident.display_name || ident.value}</span>
                <Button variant="outline" size="sm" onclick={() => doUnlink(ident.id)}>unlink</Button>
              </li>
            {/each}
          </ul>
        {/if}
        </div>
        <ScrollArea
          id="person-timeline"
          class="min-h-0 min-w-0 flex-1 px-4 pb-8"
          onscroll={onTimelineScroll}
        >
        {#if tlLoading}
          <div class="space-y-2 pt-2" aria-hidden="true">
            <Skeleton class="h-4 w-[92%]" />
            <Skeleton class="h-3 w-[68%]" />
            <Skeleton class="h-4 w-[84%]" />
            <Skeleton class="h-3 w-[56%]" />
            <Skeleton class="h-4 w-[76%]" />
          </div>
        {:else if !selectedId}
          <div class="py-6">
            <EmptyState
              title="Select a person"
              body="Click a name on the left. Groups stay hidden until you tick include groups."
              actionLabel="People"
              onAction={() => document.getElementById("person-filter")?.focus()}
            />
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
        {#if timeline.length && oldestCursor && filteredTimeline.length > 0}
          <Button
            variant="outline"
            size="sm"
            class="mb-4 mt-4"
            disabled={tlLoading}
            onclick={() => !tlLoading && selectedId && selectPerson(selectedId, true)}
            >Load older</Button
          >
        {/if}
        <ol class="min-w-0 space-y-2">
          {#if spacerTop > 0}
            <li class="timeline-spacer-top pointer-events-none" style="height: {spacerTop}px" aria-hidden="true"></li>
          {/if}
          {#each windowedDayGroups as group}
            <li class="day-group min-w-0">
              {#if utcDay(group.rows[0]?.row.sent_at)}
                <h3 class="day-heading mb-2 text-center text-xs font-medium text-muted-foreground">
                  {group.label} UTC
                </h3>
              {/if}
              <div class="space-y-2">
                {#each group.rows as item}
                  <div class="flex min-w-0" data-tl-index={item.index}>
                    <article
                      class="min-w-0 max-w-[94%] cursor-pointer rounded-2xl px-3 py-2 text-left focus-visible:ring-2 focus-visible:ring-ring {item.index ===
                      tlIndex
                        ? 'ring-2 ring-ring'
                        : ''}"
                      class:bubble-me={item.row.from_me}
                      class:bubble-them={!item.row.from_me}
                      class:ml-auto={item.row.from_me}
                      data-from-me={item.row.from_me}
                      tabindex="0"
                      aria-label={`${utcTime(item.row.sent_at)} ${displayBody(item.row.body_text || item.row.subject || "").slice(0, 80)}`}
                      onclick={() => (tlIndex = item.index)}
                      oncontextmenu={(e) => openCopyMenu(e, item.row)}
                    >
                      <p class="caption flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                        <time>{utcTime(item.row.sent_at)}</time>
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
                      {#if isMailRow(item.row)}
                        {#if (item.row.subject ?? "").trim()}
                          <p class="mail-subject mt-1 text-sm font-medium text-foreground">
                            {item.row.subject}
                          </p>
                        {/if}
                        {@const parts = splitQuotedBody(item.row.body_text || "")}
                        {#if parts.main || !parts.quoted}
                          <p class="mt-1 whitespace-pre-wrap break-words text-sm leading-normal text-foreground">
                            {displayBody(parts.main)}
                          </p>
                        {/if}
                        {#if parts.quoted}
                          {#if quotedOpen[item.row.message_id]}
                            <p
                              class="mt-1 whitespace-pre-wrap break-words text-sm leading-normal text-muted-foreground"
                            >
                              {displayBody(parts.quoted)}
                            </p>
                            <button
                              type="button"
                              class="mt-1 text-xs text-muted-foreground underline"
                              data-show-quoted
                              onclick={(e) => toggleQuoted(item.row.message_id, e)}
                              >Hide quoted</button
                            >
                          {:else}
                            <button
                              type="button"
                              class="mt-1 text-xs text-muted-foreground underline"
                              data-show-quoted
                              onclick={(e) => toggleQuoted(item.row.message_id, e)}
                              >Show quoted</button
                            >
                          {/if}
                        {/if}
                      {:else}
                        <p class="mt-1 whitespace-pre-wrap break-words text-sm leading-normal text-foreground">
                          {displayBody(item.row.body_text || item.row.subject || "")}
                        </p>
                      {/if}
                      <CasAttach items={item.row.attachments || []} onError={showErr} />
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
        <p class="shrink-0 bg-background px-4 pb-4 pt-2 text-xs text-muted-foreground">
          Bodies are text only. Day headings are UTC. <kbd class="rounded border border-border px-1">j</kbd>/<kbd
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
      class="block w-full px-3 py-1.5 text-left text-sm hover:bg-muted"
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
      <input type="checkbox" bind:checked={allowSelf} />
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
              class="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent {p.is_self
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

<ConfirmDialog
  bind:open={confirmOpen}
  title={confirmTitle}
  description={confirmDesc}
  onconfirm={async () => {
    if (confirmRun) await confirmRun();
  }}
/>
