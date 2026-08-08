<script lang="ts">
  import { onMount } from "svelte";
  import { api, type Identity, type LinkEvent, type Person, type Status, type TimelineRow } from "./lib/api";

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

  async function doMerge() {
    if (!selectedId) {
      err = "select a person first";
      return;
    }
    const other = Number(mergeInto);
    if (!other) {
      err = "enter the other person id";
      return;
    }
    if (!confirm(`Merge ${selectedId} and ${other}?`)) return;
    try {
      const out = await api.merge(selectedId, other, selectedId);
      await refreshPeople();
      await refreshEvents();
      await selectPerson(out.survivor);
    } catch (e) {
      showErr(e);
    }
  }

  async function doUnlink(id: number) {
    if (!confirm(`Unlink identity ${id}?`)) return;
    try {
      await api.unlink(id);
      if (selectedId) await selectPerson(selectedId);
      await refreshEvents();
    } catch (e) {
      showErr(e);
    }
  }

  async function doUndo(id: number, op: string) {
    if (!confirm(`Undo event ${id} (${op})?`)) return;
    try {
      await api.undo(id);
      await refreshPeople();
      await refreshEvents();
      if (selectedId) await selectPerson(selectedId);
    } catch (e) {
      showErr(e);
    }
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

<div class="flex h-full flex-col">
  <header
    class="flex items-center justify-between border-b border-zinc-200 px-4 py-2 text-sm dark:border-zinc-800"
  >
    <strong>Interlace</strong>
    <span class="text-zinc-500">offline · no account · no HTTP client</span>
  </header>

  {#if err}
    <p class="bg-red-100 px-4 py-2 text-sm text-red-900 dark:bg-red-950 dark:text-red-100">{err}</p>
  {/if}

  {#if setup}
    <main class="mx-auto w-full max-w-lg space-y-4 p-6">
      <h1 class="text-2xl font-semibold tracking-tight">Open an archive</h1>
      <p class="text-zinc-600 dark:text-zinc-400">
        Offline archive. No account. No sync. This window never phones home.
      </p>
      <label class="block text-sm">
        Phone region (ISO 3166-1 alpha-2, required)
        <input
          bind:value={region}
          maxlength="2"
          placeholder="TR"
          class="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
        />
      </label>
      <label class="block text-sm">
        Your name
        <input
          bind:value={name}
          placeholder="optional"
          class="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
        />
      </label>
      <label class="block text-sm">
        Emails (comma-separated)
        <input
          bind:value={emails}
          placeholder="optional"
          class="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
        />
      </label>
      <label class="block text-sm">
        Phones (comma-separated)
        <input
          bind:value={phones}
          placeholder="optional"
          class="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
        />
      </label>
      <div class="flex gap-2">
        <button
          type="button"
          class="rounded-md bg-zinc-900 px-3 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900"
          onclick={createArchive}>Create archive…</button
        >
        <button
          type="button"
          class="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700"
          onclick={openPicker}>Open existing…</button
        >
      </div>
      <p class="text-sm text-zinc-500">
        Folder picker only — no URLs. Phone-region has no silent default. The folder is the backup
        unit. Not encrypted at rest; use FileVault.
      </p>
    </main>
  {:else if st}
    <div class="grid min-h-0 flex-1 grid-cols-[18rem_1fr]">
      <aside class="min-h-0 overflow-auto border-r border-zinc-200 p-4 dark:border-zinc-800">
        <p class="break-all text-xs text-zinc-500">{st.path}</p>
        <dl class="mt-3 grid grid-cols-[7rem_1fr] gap-x-2 gap-y-1 text-sm">
          <dt class="text-zinc-500">owner</dt>
          <dd>{st.owner_display_name || "—"}</dd>
          <dt class="text-zinc-500">region</dt>
          <dd>{st.default_phone_region || "—"}</dd>
          <dt class="text-zinc-500">messages</dt>
          <dd>{st.messages}</dd>
          <dt class="text-zinc-500">identities</dt>
          <dd>{st.identities}</dd>
          <dt class="text-zinc-500">persons</dt>
          <dd>{st.persons_live}</dd>
          <dt class="text-zinc-500">review</dt>
          <dd>{st.review_open}</dd>
        </dl>
        <p class="mt-2 text-xs text-zinc-500">
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
        <label class="mt-4 block text-sm">
          Filter people
          <input
            id="person-filter"
            bind:value={filter}
            type="search"
            placeholder="name"
            class="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>
        <ul class="mt-2 space-y-0.5">
          {#each filtered as p}
            <li>
              <button
                type="button"
                class="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-zinc-100 dark:hover:bg-zinc-900 {selectedId ===
                p.id
                  ? 'bg-zinc-200 dark:bg-zinc-800'
                  : ''} {p.is_self ? 'font-semibold' : ''}"
                onclick={() => selectPerson(p.id)}
              >
                {p.is_self ? `${p.display_name} (self)` : p.display_name}
              </button>
            </li>
          {/each}
        </ul>
        <div class="mt-4 space-y-2">
          <label class="block text-sm">
            Merge into id
            <input
              bind:value={mergeInto}
              inputmode="numeric"
              placeholder="person id"
              class="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          </label>
          <button
            type="button"
            class="rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700"
            onclick={doMerge}>Merge selected →</button
          >
        </div>
        <ul class="mt-3 space-y-1 text-xs">
          {#each events as e}
            <li class="flex items-center justify-between gap-2">
              <span>#{e.id} {e.op}</span>
              <button
                type="button"
                class="rounded border border-zinc-300 px-2 py-0.5 dark:border-zinc-700"
                onclick={() => doUndo(e.id, e.op)}>undo</button
              >
            </li>
          {/each}
        </ul>
        <button
          type="button"
          class="mt-4 rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700"
          onclick={openPicker}>Open other archive…</button
        >
      </aside>
      <section class="min-h-0 overflow-auto p-4">
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
        <ul class="mb-3 space-y-1 text-sm text-zinc-600 dark:text-zinc-400">
          {#each identities as ident}
            <li class="flex items-center justify-between gap-2">
              <span>{ident.platform} {ident.kind} {ident.display_name || ident.value}</span>
              <button
                type="button"
                class="rounded border border-zinc-300 px-2 py-0.5 text-xs dark:border-zinc-700"
                onclick={() => doUnlink(ident.id)}>unlink</button
              >
            </li>
          {/each}
        </ul>
        <ol class="divide-y divide-zinc-200 dark:divide-zinc-800">
          {#each timeline as row, i}
            <li>
              <button
                type="button"
                class="w-full px-1 py-2 text-left {i === tlIndex ? 'bg-zinc-100 dark:bg-zinc-900' : ''}"
                onclick={() => (tlIndex = i)}
              >
                <div class="text-xs text-zinc-500">
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
                <p class="mt-1 whitespace-pre-wrap text-sm">{row.body_text || row.subject || ""}</p>
              </button>
            </li>
          {/each}
        </ol>
        {#if timeline.length}
          <button
            type="button"
            class="mt-3 rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700"
            onclick={() => selectedId && selectPerson(selectedId, true)}>Load older</button
          >
        {/if}
        <p class="mt-4 text-xs text-zinc-500">
          Bodies are text only. <kbd class="rounded border border-zinc-300 px-1 dark:border-zinc-700">j</kbd>/<kbd
            class="rounded border border-zinc-300 px-1 dark:border-zinc-700">k</kbd
          >
          move.
          <kbd class="rounded border border-zinc-300 px-1 dark:border-zinc-700">/</kbd> filters people.
        </p>
      </section>
    </div>
  {/if}
</div>
