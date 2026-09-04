<script lang="ts">
  import { onMount, tick } from "svelte";
  import { getCurrentWindow } from "@tauri-apps/api/window";
  import { api, type Identity, type LinkEvent, type Person, type Status } from "./lib/api";
  import { Card } from "$lib/components/ui/card/index.js";
  import { Toast } from "$lib/components/ui/toast/index.js";
  import ConfirmDialog from "$lib/ConfirmDialog.svelte";
  import CommandPalette from "$lib/CommandPalette.svelte";
  import SearchPane from "$lib/SearchPane.svelte";
  import ReviewPane from "$lib/ReviewPane.svelte";
  import ImportPane from "$lib/ImportPane.svelte";
  import DoctorPane from "$lib/DoctorPane.svelte";
  import SetupScreen from "$lib/SetupScreen.svelte";
  import PeopleShell from "$lib/PeopleShell.svelte";
  import PeopleNav from "$lib/PeopleNav.svelte";
  import { friendly, isDroppedUrl } from "./lib/PeopleFriendly";
  import { handleAppKey } from "./lib/PeopleKeys";
  import { startPeopleBoot } from "./lib/PeopleBoot";
  import {
    type Density, readDensityPref, readIncludeGroupsPref, readLastPersonId, readLastView, readPeopleSortPref, readSidebarPref,
    writeDensityPref, writeLastPerson, writeLastView, writeSidebarPref,
  } from "./lib/PeoplePrefs";
  import { personLabel } from "./lib/PeopleUndo";

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
  let tlIndex = $state(0);
  let includeGroups = $state(false); let peopleSort = $state("recent");
  let showPersonChrome = $state(false);
  let events = $state<LinkEvent[]>([]);

  let confirmOpen = $state(false);
  let confirmTitle = $state("");
  let confirmDesc = $state("");
  let confirmLabel = $state("Confirm");
  let confirmRun = $state<(() => Promise<void>) | null>(null);
  let view = $state<"people" | "search" | "review" | "import" | "doctor">("people");
  let commandOpen = $state(false);
  let searchQ = $state("");
  let seedPerson = $state<Person | null>(null);
  let booting = $state(true);
  let opening = $state(false);
  let peopleLoading = $state(true);
  let peopleGen = 0;
  let doctor = $state<string[]>([]);
  let visibleTlIndices = $state<number[]>([]);
  const personInspectorAttr = ["data", "person", "inspector"].join("-");
  let peopleShell: {
    pane: () => { selectPerson: (id: number, append?: boolean, keepConversation?: boolean) => Promise<void>; openPersonAtMessage: (a: number, b: number, c?: string | null) => Promise<void>; ensureTlIndexVisible: (n: number) => void; closeCopyMenu: () => void } | undefined;
    filteredIds: () => number[];
  } | undefined = $state();

  const cloudWarning = $derived(
    (st?.warnings ?? []).find((w) =>
      /iCloud|Mobile Documents|Dropbox|Google Drive/i.test(w),
    ),
  );

  const windowTitle = $derived.by(() => {
    if (setup || booting || !st) return "Interlace";
    if (view === "search") return "Search — Interlace";
    if (view === "review") return "Review — Interlace";
    if (view === "import") return "Import — Interlace";
    if (view === "doctor") return "Doctor — Interlace";
    if (selectedId != null && personTitle && personTitle !== "Select a person") return personTitle + " — Interlace";
    return "Interlace";
  });

  $effect(() => { void getCurrentWindow().setTitle(windowTitle).catch(() => {}); });
  $effect(() => { document.documentElement.dataset.density = density; });

  let viewRestored = false;
  let personRestored = false;
  let userCollapsed = $state(false);
  let density = $state<Density>("default");
  let narrow = $state(false);
  let forceOpen = $state(false);
  const sidebarCollapsed = $derived(userCollapsed || (narrow && !forceOpen));

  function persistSidebar(next: boolean) {
    userCollapsed = next;
    forceOpen = !next;
    writeSidebarPref(next);
  }
  function persistDensity(next: Density) {
    density = next;
    writeDensityPref(next);
  }
  function persistLastPerson(id: number) {
    writeLastPerson(id);
  }
  $effect(() => {
    void view;
    if (!viewRestored) return;
    writeLastView(view);
  });
  function restoreLastView() {
    if (viewRestored) return;
    view = readLastView();
    viewRestored = true;
  }
  function restoreLastPerson() {
    if (personRestored) return;
    personRestored = true;
    const id = selectedId != null ? null : readLastPersonId();
    if (id != null && people.some((p) => p.id === id)) void peopleShell?.pane()?.selectPerson(id);
  }
  function syncNarrow() {
    const next = window.innerWidth < 880;
    if (next && !narrow) forceOpen = false;
    narrow = next;
  }

  function showErr(e: unknown) {
    err = friendly(e instanceof Error ? e.message : String(e ?? ""));
  }
  let toastSeq = 0;
  let toasts = $state<{ id: number; message: string }[]>([]);
  function showToast(message: string) {
    const id = ++toastSeq;
    toasts = [...toasts, { id, message }];
    window.setTimeout(() => { toasts = toasts.filter((item) => item.id !== id); }, 2500);
  }
  async function revealArchive() {
    try { await api.revealArchive(); } catch { showToast("Could not reveal"); }
  }
  async function importDroppedPaths(paths: string[]) {
    if (setup) return;
    const local = paths.find((p) => p && p.trim() && !isDroppedUrl(p));
    if (!local) {
      if (paths.some((p) => (p ?? "").trim())) showToast("Drop a local ZIP or mbox — URLs are not imported.");
      return;
    }
    err = "";
    view = "import";
    try { await api.importStart({ path: local }); } catch (e) { showErr(e); }
  }

  function ask(title: string, description: string, run: () => Promise<void>, label = "Confirm") {
    confirmTitle = title;
    confirmDesc = description;
    confirmLabel = label;
    confirmRun = run;
    confirmOpen = true;
  }
  function openUrl(url: string) {
    ask("Open this link?", url, async () => {
      await api.openUrl(url);
    }, "Open link");
  }
  async function refreshPeople() {
    const gen = ++peopleGen;
    peopleLoading = true;
    try {
      const next = await api.people();
      if (gen !== peopleGen) return;
      people = next;
      restoreLastPerson();
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
    includeGroups = readIncludeGroupsPref(); peopleSort = readPeopleSortPref();
    void refreshPeople().catch(showErr);
    await refreshEvents();
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

  function searchFromBubble() {
    const p = people.find((x) => x.id === selectedId);
    if (p) {
      searchQ = p.display_name;
      seedPerson = p;
    }
    void whenSearchPaneReady().then((qEl) => {
      qEl?.focus();
      seedPerson = null;
    });
  }
  async function jumpToMessage(args: {
    personId: number;
    messageId: number;
    conversationKind?: string | null;
    sentAt?: string | null;
  }) {
    view = "people";
    if ((args.conversationKind ?? "").toLowerCase() === "group" && !includeGroups) {
      includeGroups = true;
    }
    await tick();
    await peopleShell?.pane()?.openPersonAtMessage(args.personId, args.messageId, args.sentAt);
  }

  async function whenSearchPaneReady(): Promise<HTMLInputElement | null> {
    if (setup) return null;
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
    void whenSearchPaneReady().then((qEl) => { qEl?.focus(); qEl?.form?.requestSubmit(); });
  }
  function runCommandView(next: "people" | "search" | "review" | "import" | "doctor") {
    if (setup) return;
    commandOpen = false;
    if (next === "search") void whenSearchPaneReady().then((qEl) => qEl?.focus());
    else view = next;
  }
  function runCommandPerson(p: Person) {
    view = "people";
    void peopleShell?.pane()?.selectPerson(p.id);
    commandOpen = false;
  }
  function runCommandDensity(next: Density) { persistDensity(next); commandOpen = false; }

  function onKey(e: KeyboardEvent) {
    const t = e.target as HTMLElement | null;
    const mod = e.metaKey || (e.ctrlKey && !e.altKey);
    if (commandOpen && e.key === "Escape") { commandOpen = false; e.preventDefault(); return; }
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT") && !(mod && (e.key === "\\" || e.code === "Backslash" || e.code === "IntlBackslash" || e.key === "f" || e.key === "F" || e.key === "k" || e.key === "K" || /[1-5]/.test(e.key)))) {
      if (e.key === "Escape") t.blur();
      return;
    }
    if (e.key === "Escape" && !commandOpen) view = "people";
    handleAppKey(e, {
      commandOpen,
      setCommandOpen: (v) => { commandOpen = v; },
      view,
      setView: (v) => { if (setup) return; view = v; },
      sidebarCollapsed,
      persistSidebar,
      showPersonChrome,
      setShowPersonChrome: (v) => { showPersonChrome = v; },
      personInspectorAttr,
      closeCopyMenu: () => peopleShell?.pane()?.closeCopyMenu(),
      whenSearchPaneReady,
      filteredIds: peopleShell?.filteredIds() ?? [],
      selectedId,
      selectPerson: (id) => { void peopleShell?.pane()?.selectPerson(id); },
      visibleTlIndices,
      tlIndex,
      setTlIndex: (n) => { tlIndex = n; },
      ensureTlIndexVisible: (n) => peopleShell?.pane()?.ensureTlIndexVisible(n),
      scrollToLatest: () => peopleShell?.pane()?.scrollToLatest(),
    });
    void (e.key === "j" || e.key === "k");
  }

  onMount(() => {
    userCollapsed = readSidebarPref();
    density = readDensityPref();
    includeGroups = readIncludeGroupsPref(); peopleSort = readPeopleSortPref();
    restoreLastView();
    syncNarrow();
    window.addEventListener("resize", syncNarrow);
    window.addEventListener("keydown", onKey);
    const stopBoot = startPeopleBoot({
      openPicker,
      setView: (v) => { if (setup) return; view = v; },
      importDroppedPaths,
      openPath,
      showErr, get err() { return err; }, set err(v) { err = v; },
      setSetup: (v) => {
        setup = v;
        if (v) { people = []; selectedId = null; events = []; st = null; doctor = []; filter = ""; searchQ = ""; seedPerson = null; includeGroups = false; identities = []; personTitle = "Select a person"; view = "people"; ++peopleGen; confirmOpen = false; confirmRun = null; }
      },
      setBooting: (v) => { booting = v; },
    });
    return () => {
      stopBoot();
      window.removeEventListener("resize", syncNarrow);
      window.removeEventListener("keydown", onKey);
    };
  });
</script>

<!-- This window never phones home. -->
<div class="flex h-full flex-col bg-background text-foreground" data-density={density}>
  <header
    class="flex items-center justify-end border-b border-border py-2 pl-20 pr-4 text-sm"
    data-tauri-drag-region
  >
    <span class="text-muted-foreground">offline · no account · no HTTP client</span>
  </header>
  {#if !setup && st}
    <PeopleNav
      bind:view
      bind:searchQ
      {density}
      {st}
      doctorCount={doctor.length}
      {booting}
      {opening}
      {persistDensity}
      onSearchSubmit={submitChromeSearch}
    />
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

  {#if doctor.length}
    <div class="min-w-0 rounded-none border-x-0 border-t-0 border-b border-warning bg-warning/15 px-4 py-2 text-sm text-warning">
      <p class="font-medium">Doctor found {doctor.length} issue{doctor.length === 1 ? "" : "s"}</p>
      <ul class="mt-1 min-w-0 list-disc pl-4">
        {#each doctor as d}
          <li class="break-words">{d}</li>
        {/each}
      </ul>
      <p class="mt-1 text-xs">Open the Doctor tab to run integrity, rebuild FTS, or GC CAS in-app.</p>
    </div>
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
    <SetupScreen
      bind:region
      bind:name
      bind:emails
      bind:phones
      onError={showErr}
      {applyStatus}
      onOpenExisting={openPicker}
      onBegin={() => {
        err = "";
        doctor = [];
      }}
    />
  {:else if st && view === "search"}
    <SearchPane
      bind:q={searchQ}
      {people}
      {friendly}
      {seedPerson}
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
      onToast={showToast}
      onDone={async () => {
        await applyStatus(await api.status());
      }}
      onGoPeople={() => (view = "people")}
    />
  {:else if st}
    <PeopleShell
      bind:this={peopleShell}
      {st}
      {people}
      bind:events
      bind:filter
      bind:selectedId
      bind:personTitle
      bind:identities
      bind:includeGroups bind:peopleSort
      bind:tlIndex
      bind:visibleTlIndices
      bind:showPersonChrome
      {peopleLoading}
      {sidebarCollapsed}
      {density}
      {persistSidebar}
      {persistLastPerson}
      {friendly}
      {showErr}
      {showToast}
      {openUrl}
      {ask}
      onImport={() => (view = "import")}
      onOpenPicker={openPicker}
      onReveal={revealArchive}
      onSearchFromBubble={searchFromBubble}
      onPeopleChanged={refreshPeople}
    />
  {/if}
</div>

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
  confirmLabel={confirmLabel}
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
    onDensity={runCommandDensity}
    onClose={() => (commandOpen = false)}
  />
{/if}
