<script lang="ts">
  import { onMount, tick } from "svelte";
  import { api, type Identity, type LinkEvent, type Person, type PersonConversation, type Status, type TimelineRow } from "./lib/api";
  import { mergeTargets } from "./lib/utils";
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Label } from "$lib/components/ui/label/index.js";
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import ConfirmDialog from "$lib/ConfirmDialog.svelte";
  import SearchPane from "$lib/SearchPane.svelte";
  import ReviewPane from "$lib/ReviewPane.svelte";
  import ImportPane from "$lib/ImportPane.svelte";
  import DoctorPane from "$lib/DoctorPane.svelte";
  import EmptyState from "$lib/EmptyState.svelte";
  import CasAttach from "$lib/CasAttach.svelte";

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
  let tlGen = 0;
  let doctor = $state<string[]>([]);
  let pinLatestObs: ResizeObserver | null = null;
  let pinLatestUntil: ReturnType<typeof setTimeout> | null = null;

  const cloudWarning = $derived(
    (st?.warnings ?? []).find((w) =>
      /iCloud|Mobile Documents|Dropbox|Google Drive/i.test(w),
    ),
  );

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

  function csv(s: string) {
    return s.split(",").map((x) => x.trim()).filter(Boolean);
  }

  function displayBody(s: string) {
    return s.replace(/<attached:\s*[^>]+>/gi, "").trim();
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

  const dayGroups = $derived.by(() => {
    const groups: { key: string; label: string; rows: { row: TimelineRow; index: number }[] }[] =
      [];
    for (let i = 0; i < timeline.length; i++) {
      const row = timeline[i];
      const key = utcDay(row.sent_at);
      const dayChanged = key !== utcDay(timeline[i - 1]?.sent_at);
      const last = groups[groups.length - 1];
      if (!last || dayChanged) {
        groups.push({ key, label: key ? utcDayLabel(row.sent_at) : "", rows: [{ row, index: i }] });
      } else {
        last.rows.push({ row, index: i });
      }
    }
    return groups;
  });

  function ask(title: string, description: string, run: () => Promise<void>) {
    confirmTitle = title;
    confirmDesc = description;
    confirmRun = run;
    confirmOpen = true;
  }

  async function refreshPeople() {
    people = await api.people();
  }

  async function refreshEvents() {
    events = await api.linkEvents();
  }

  async function applyStatus(next: Status) {
    st = next;
    setup = false;
    await refreshPeople();
    await refreshEvents();
    try {
      doctor = await api.doctorIssues();
    } catch {
      doctor = [];
    }
  }

  async function openPath(path: string) {
    err = "";
    opening = true;
    try {
      await applyStatus(await api.open(path));
    } finally {
      opening = false;
    }
  }

  async function createArchive() {
    err = "";
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
  }

  function watchPinLatest(sc: HTMLElement) {
    stopPinLatest();
    pinTimelineLatest(sc);
    const ol = sc.querySelector("ol");
    pinLatestObs = new ResizeObserver(() => {
      sc.scrollTop = sc.scrollHeight;
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

  /** Empty / person-name titles → WhatsApp, Gmail, …; keep group names and subjects. */
  function conversationLabel(title: string | null | undefined, platform: string | null | undefined) {
    if (
      !(title ?? "").trim() ||
      (title ?? "").trim().toLowerCase() === personTitle.trim().toLowerCase()
    ) {
      const p = (platform ?? "").trim().toLowerCase();
      if (p === "whatsapp") return "WhatsApp";
      if (p === "gmail") return "Gmail";
      if (p === "contacts") return "Contacts";
      if (!p) return "";
      return p.charAt(0).toUpperCase() + p.slice(1);
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
        }
      } else {
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
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) {
      if (e.key === "Escape") t.blur();
      return;
    }
    if (e.key === "/") {
      e.preventDefault();
      document.getElementById("person-filter")?.focus();
      return;
    }
    if (!timeline.length) return;
    if (e.key === "j" || e.key === "ArrowDown") {
      tlIndex = Math.min(timeline.length - 1, tlIndex + 1);
      e.preventDefault();
    }
    if (e.key === "k" || e.key === "ArrowUp") {
      tlIndex = Math.max(0, tlIndex - 1);
      e.preventDefault();
    }
  }

  onMount(() => {
    window.addEventListener("keydown", onKey);
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
      window.removeEventListener("keydown", onKey);
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
        >People</Button
      >
      <Button size="sm" variant={view === "search" ? "default" : "ghost"} onclick={() => (view = "search")}
        >Search</Button
      >
      <Button size="sm" variant={view === "review" ? "default" : "ghost"} onclick={() => (view = "review")}
        >Review{#if st.review_open} ({st.review_open}){/if}</Button
      >
      <Button size="sm" variant={view === "import" ? "default" : "ghost"} onclick={() => (view = "import")}
        >Import</Button
      >
      <Button size="sm" variant={view === "doctor" ? "default" : "ghost"} onclick={() => (view = "doctor")}
        >Doctor{#if doctor.length} ({doctor.length}){/if}</Button
      >
    </nav>
  {/if}

  {#if err}
    <p class="whitespace-pre-wrap bg-destructive/15 px-4 py-2 text-sm text-destructive">{err}</p>
  {/if}

  {#if st && cloudWarning}
    <div
      class="border-b border-amber-700/40 bg-amber-950/15 px-4 py-2 text-sm text-amber-900 dark:text-amber-200"
      data-cloud-warning
    >
      <p class="font-medium">This archive looks like it sits on iCloud, Dropbox, or Google Drive.</p>
      <p class="mt-0.5">
        The folder is the backup unit. Not encrypted at rest — FileVault is your encryption. Move the
        live folder off cloud sync; see <code class="text-xs">docs/user/backup.md</code>.
      </p>
    </div>
  {/if}

  {#if booting || opening}
    <main class="flex h-full flex-col items-center justify-center gap-3 p-6">
      <div
        class="h-8 w-8 animate-spin rounded-full border-2 border-muted border-t-foreground"
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
      <h1 class="text-2xl font-semibold tracking-tight">Open an archive</h1>
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
        <Button onclick={createArchive}>Create archive…</Button>
        <Button variant="outline" onclick={openPicker}>Open existing…</Button>
      </div>
      <p class="text-sm text-muted-foreground">
        Folder picker only — no URLs. Phone-region has no silent default. The folder is the backup
        unit. Not encrypted at rest; use FileVault.
      </p>
    </main>
  {:else if st && view === "search"}
    <SearchPane {people} onError={showErr} />
  {:else if st && view === "review"}
    <ReviewPane
      onError={showErr}
      onChanged={async () => {
        await applyStatus(await api.status());
      }}
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
          <ul class="mt-2 min-w-0 list-disc pl-4 text-sm text-amber-700 dark:text-amber-400">
            {#each st.warnings as w}
              <li class="break-words">{w}</li>
            {/each}
          </ul>
        {/if}
        {#if doctor.length}
          <div class="mt-2 min-w-0 rounded-md border border-amber-700/40 bg-amber-950/20 p-2 text-sm text-amber-800 dark:text-amber-300">
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
        <ul class="mt-2 min-w-0 space-y-0.5">
          {#each filtered as p}
            <li class="min-w-0">
              <button
                type="button"
                class="w-full min-w-0 max-w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent {selectedId ===
                p.id
                  ? 'bg-accent'
                  : ''} {p.is_self ? 'font-semibold' : ''}"
                onclick={() => selectPerson(p.id)}
              >
                <span class="block truncate">{p.is_self ? `${p.display_name} (self)` : p.display_name}</span>
                {#if p.last_activity_at || p.preview}
                  <span class="mt-0.5 block truncate text-xs font-normal text-muted-foreground">
                    {p.last_activity_at ?? ""}{p.last_activity_at && p.preview ? " · " : ""}{p.preview ?? ""}
                  </span>
                {/if}
              </button>
            </li>
          {/each}
        </ul>
        {#if people.length === 0}
          <div class="mt-3 min-w-0">
            <EmptyState
              title="No people yet"
              body="Import a WhatsApp ZIP or Takeout from the Import tab. Name-only chats become people after import."
            />
          </div>
        {:else if filtered.length === 0}
          <div class="mt-3 min-w-0">
            <EmptyState title="No match" body="Clear the filter or try another spelling." />
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
          {#if selectedId}
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
        </div>
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
        <ScrollArea id="person-timeline" class="min-h-0 min-w-0 flex-1 px-4 pb-8">
        {#if tlLoading}
          <p class="text-sm text-muted-foreground">Loading timeline…</p>
        {:else if !selectedId}
          <EmptyState
            title="Select a person"
            body="Click a name on the left. Groups stay hidden until you tick include groups."
          />
        {:else if timeline.length === 0}
          <EmptyState
            title="No messages in this view"
            body="This person may only appear in groups. Tick include groups, or import more sources."
          />
        {/if}
        {#if timeline.length && oldestCursor}
          <Button
            variant="outline"
            size="sm"
            class="mb-3"
            disabled={tlLoading}
            onclick={() => !tlLoading && selectedId && selectPerson(selectedId, true)}
            >Load older</Button
          >
        {/if}
        <ol class="min-w-0 space-y-2">
          {#each dayGroups as group}
            <li class="day-group min-w-0">
              {#if utcDay(group.rows[0]?.row.sent_at)}
                <h3 class="day-heading mb-2 text-center text-xs font-medium text-muted-foreground">
                  {group.label} UTC
                </h3>
              {/if}
              <div class="space-y-2">
                {#each group.rows as item}
                  <div class="flex min-w-0">
                    <button
                      type="button"
                      class="min-w-0 max-w-[94%] rounded-2xl px-3 py-2 text-left {item.index ===
                      tlIndex
                        ? 'ring-2 ring-ring'
                        : ''}"
                      class:bubble-me={item.row.from_me}
                      class:bubble-them={!item.row.from_me}
                      class:ml-auto={item.row.from_me}
                      data-from-me={item.row.from_me}
                      onclick={() => (tlIndex = item.index)}
                    >
                      <p class="caption text-xs text-muted-foreground">
                        <time>{utcTime(item.row.sent_at)}</time>
                        {item.row.platform}
                      </p>
                      <p class="mt-1 whitespace-pre-wrap break-words text-sm text-foreground">{displayBody(item.row.body_text || item.row.subject || "")}</p>
                      <CasAttach items={item.row.attachments || []} />
                    </button>
                  </div>
                {/each}
              </div>
            </li>
          {/each}
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
                  {p.last_activity_at ?? ""}{p.last_activity_at && p.preview ? " · " : ""}{p.preview ?? ""}
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
