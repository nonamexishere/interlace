<script lang="ts">
  import { onMount } from "svelte";
  import { api, type Identity, type LinkEvent, type Person, type Status, type TimelineRow } from "./lib/api";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Label } from "$lib/components/ui/label/index.js";
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import ConfirmDialog from "$lib/ConfirmDialog.svelte";

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

  const filtered = $derived(
    people.filter((p) => {
      const q = filter.trim().toLowerCase();
      if (!q) return true;
      return (p.display_name + (p.is_self ? " self" : "")).toLowerCase().includes(q);
    }),
  );

  function showErr(e: unknown) {
    err = e instanceof Error ? e.message : String(e ?? "");
  }

  function csv(s: string) {
    return s.split(",").map((x) => x.trim()).filter(Boolean);
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
  }

  async function openPath(path: string) {
    err = "";
    await applyStatus(await api.open(path));
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

  {#if err}
    <p class="bg-destructive/15 px-4 py-2 text-sm text-destructive">{err}</p>
  {/if}

  {#if setup}
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
                <p class="mt-1 whitespace-pre-wrap text-sm text-foreground">{row.body_text || row.subject || ""}</p>
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
