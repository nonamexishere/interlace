<script lang="ts">
  import { onMount } from "svelte";
  import { api, type Identity, type LinkEvent, type Person, type Status, type TimelineRow } from "./lib/api";
  import { Button } from "$lib/components/ui/button/index.js";
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
  let mergeInto = $state("");
  let events = $state<LinkEvent[]>([]);

  let confirmOpen = $state(false);
  let confirmTitle = $state("");
  let confirmDesc = $state("");
  let confirmRun = $state<(() => Promise<void>) | null>(null);
  let view = $state<"people" | "search" | "review" | "import" | "doctor">("people");
  let booting = $state(true);
  let opening = $state(false);
  let tlLoading = $state(false);
  let doctor = $state<string[]>([]);

  const cloudWarning = $derived(
    (st?.warnings ?? []).find((w) =>
      /iCloud|Mobile Documents|Dropbox|Google Drive/i.test(w),
    ),
  );

  const filtered = $derived(
    people.filter((p) => {
      const q = filter.trim().toLowerCase();
      if (!q) return true;
      return (p.display_name + (p.is_self ? " self" : "")).toLowerCase().includes(q);
    }),
  );

  function friendly(raw: string): string {
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

  async function selectPerson(id: number, append = false) {
    selectedId = id;
    tlLoading = true;
    try {
      const show = await api.personShow(id);
      personTitle = show.display_name || `person ${id}`;
      identities = show.identities || [];
      const before = append && timeline.length ? timeline[timeline.length - 1].sent_at : null;
      const rows = await api.personTimeline({
        id,
        includeGroups,
        limit: 80,
        before: before ?? null,
      });
      timeline = append ? timeline.concat(rows) : rows;
      tlIndex = 0;
    } catch (e) {
      showErr(e);
    } finally {
      tlLoading = false;
    }
  }

  function doMerge() {
    if (!selectedId) {
      err = "select a person first";
      return;
    }
    const other = Number(mergeInto);
    if (!other) {
      err = "enter the other person id";
      return;
    }
    const keep = selectedId;
    ask(`Merge ${selectedId} and ${other}?`, "Identity links move. Message rows are not rewritten.", async () => {
      const out = await api.merge(keep, other, keep);
      await refreshPeople();
      await refreshEvents();
      await selectPerson(out.survivor);
    });
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
      } finally {
        booting = false;
      }
      setup = true;
    })();
    return () => window.removeEventListener("keydown", onKey);
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
    <main class="mx-auto w-full max-w-lg space-y-2 p-6">
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
    <div class="grid min-h-0 flex-1 grid-cols-[18rem_1fr]">
      <ScrollArea class="border-r border-border p-4">
        <p class="break-all text-xs text-muted-foreground">{st.path}</p>
        <dl class="mt-3 grid grid-cols-[7rem_1fr] gap-x-2 gap-y-1 text-sm">
          <dt class="text-muted-foreground">owner</dt>
          <dd>{st.owner_display_name || "—"}</dd>
          <dt class="text-muted-foreground">region</dt>
          <dd>{st.default_phone_region || "—"}</dd>
          <dt class="text-muted-foreground">messages</dt>
          <dd>{st.messages}</dd>
          <dt class="text-muted-foreground">identities</dt>
          <dd>{st.identities}</dd>
          <dt class="text-muted-foreground">persons</dt>
          <dd>{st.persons_live}</dd>
          <dt class="text-muted-foreground">review</dt>
          <dd>{st.review_open}</dd>
        </dl>
        <p class="mt-2 text-xs text-muted-foreground">
          {st.last_import
            ? `last import id=${st.last_import.id} status=${st.last_import.status}`
            : "no imports yet"}
        </p>
        {#if st.warnings?.length}
          <ul class="mt-2 list-disc pl-4 text-sm text-amber-700 dark:text-amber-400">
            {#each st.warnings as w}
              <li>{w}</li>
            {/each}
          </ul>
        {/if}
        {#if doctor.length}
          <div class="mt-2 rounded-md border border-amber-700/40 bg-amber-950/20 p-2 text-sm text-amber-800 dark:text-amber-300">
            <p class="font-medium">Doctor found {doctor.length} issue{doctor.length === 1 ? "" : "s"}</p>
            <ul class="mt-1 list-disc pl-4">
              {#each doctor as d}
                <li>{d}</li>
              {/each}
            </ul>
            <p class="mt-1 text-xs">Open the Doctor tab to run integrity, rebuild FTS, or GC CAS in-app.</p>
          </div>
        {/if}
        <div class="mt-4 space-y-1.5">
          <Label for="person-filter">Filter people</Label>
          <Input id="person-filter" type="search" bind:value={filter} placeholder="name" />
        </div>
        <ul class="mt-2 space-y-0.5">
          {#each filtered as p}
            <li>
              <button
                type="button"
                class="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent {selectedId ===
                p.id
                  ? 'bg-accent'
                  : ''} {p.is_self ? 'font-semibold' : ''}"
                onclick={() => selectPerson(p.id)}
              >
                {p.is_self ? `${p.display_name} (self)` : p.display_name}
              </button>
            </li>
          {/each}
        </ul>
        {#if people.length === 0}
          <div class="mt-3">
            <EmptyState
              title="No people yet"
              body="Import a WhatsApp ZIP or Takeout from the Import tab. Name-only chats become people after import."
            />
          </div>
        {:else if filtered.length === 0}
          <div class="mt-3">
            <EmptyState title="No match" body="Clear the filter or try another spelling." />
          </div>
        {/if}
        <div class="mt-4 space-y-2">
          <div class="space-y-1.5">
            <Label for="merge-into">Merge into id</Label>
            <Input id="merge-into" bind:value={mergeInto} inputmode="numeric" placeholder="person id" />
          </div>
          <Button variant="outline" size="sm" onclick={doMerge}>Merge selected →</Button>
        </div>
        <ul class="mt-3 space-y-1 text-xs">
          {#each events as e}
            <li class="flex items-center justify-between gap-2">
              <span>#{e.id} {e.op}</span>
              <Button variant="outline" size="sm" onclick={() => doUndo(e.id, e.op)}>undo</Button>
            </li>
          {/each}
        </ul>
        <Button variant="outline" size="sm" class="mt-4" onclick={openPicker}>Open other archive…</Button>
      </ScrollArea>
      <ScrollArea class="p-4">
        <div class="mb-3 flex items-baseline justify-between gap-3">
          <h1 class="text-xl font-semibold tracking-tight">{personTitle}</h1>
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
        <ol class="divide-y divide-border">
          {#each timeline as row, i}
            <li>
              <button
                type="button"
                class="w-full px-1 py-2 text-left {i === tlIndex ? 'bg-accent' : ''}"
                onclick={() => (tlIndex = i)}
              >
                <div class="text-xs text-muted-foreground">
                  {[
                    row.sent_at || "no date",
                    row.platform,
                    row.conversation_kind,
                    row.from_me ? "you" : "them",
                    row.conversation_title || "",
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </div>
                <p class="mt-1 whitespace-pre-wrap text-sm text-foreground">{displayBody(row.body_text || row.subject || "")}</p>
                <CasAttach items={row.attachments || []} />
              </button>
            </li>
          {/each}
        </ol>
        {#if timeline.length}
          <Button variant="outline" size="sm" class="mt-3" onclick={() => selectedId && selectPerson(selectedId, true)}
            >Load older</Button
          >
        {/if}
        <p class="mt-4 text-xs text-muted-foreground">
          Bodies are text only. <kbd class="rounded border border-border px-1">j</kbd>/<kbd
            class="rounded border border-border px-1">k</kbd
          >
          move.
          <kbd class="rounded border border-border px-1">/</kbd> filters people.
        </p>
      </ScrollArea>
    </div>
  {/if}
</div>

<ConfirmDialog
  bind:open={confirmOpen}
  title={confirmTitle}
  description={confirmDesc}
  onconfirm={async () => {
    if (confirmRun) await confirmRun();
  }}
/>
