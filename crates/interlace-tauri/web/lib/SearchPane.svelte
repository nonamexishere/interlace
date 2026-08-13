<script lang="ts">
  import { api, type Person, type SearchHit } from "./api";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Label } from "$lib/components/ui/label/index.js";
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import EmptyState from "./EmptyState.svelte";
  import CasAttach from "./CasAttach.svelte";

  let { people, onError }: { people: Person[]; onError: (e: unknown) => void } = $props();

  let q = $state("");
  /** Stored person_id for api.search; null when cleared / no pick. */
  let personId = $state<number | null>(null);
  let personFilter = $state("");
  let personListOpen = $state(false);
  let personHighlight = $state(0);
  let from = $state("");
  let to = $state("");
  let platform = $state("");
  let conversationKind = $state("");
  let includeGroups = $state(false);
  let hits = $state<SearchHit[]>([]);
  let expanded = $state<number | null>(null);
  let body = $state("");
  let empty = $state(false);
  let searched = $state(false);
  let searching = $state(false);

  function personLabel(p: Person) {
    return p.is_self ? `${p.display_name} (self)` : p.display_name;
  }

  const filteredPeople = $derived(
    people.filter((p) => {
      const needle = personFilter.trim().toLowerCase();
      if (!needle) return true;
      const hay = (p.display_name + (p.is_self ? " self" : "")).toLowerCase();
      return hay.includes(needle);
    }),
  );

  function pickPerson(p: Person) {
    personId = p.id;
    personFilter = personLabel(p);
    personListOpen = false;
  }

  function clearPerson() {
    personId = null;
    personFilter = "";
    personHighlight = 0;
    personListOpen = false;
  }

  function onPersonFilterInput() {
    // Typing invalidates a previous pick so search does not keep a stale id.
    personId = null;
    personListOpen = true;
    personHighlight = 0;
  }

  function onPersonKeydown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      e.stopPropagation();
      // Need a name query so Enter does not grab the first of the full list.
      if (!personFilter.trim()) return;
      const list = filteredPeople;
      if (list.length > 0) {
        const idx = Math.min(Math.max(0, personHighlight), list.length - 1);
        pickPerson(list[idx]);
      }
      return;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      clearPerson();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      personListOpen = true;
      if (filteredPeople.length > 0) {
        personHighlight = Math.min(personHighlight + 1, filteredPeople.length - 1);
      }
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      personHighlight = Math.max(personHighlight - 1, 0);
    }
  }

  async function run() {
    empty = false;
    searched = true;
    searching = true;
    expanded = null;
    body = "";
    try {
      hits = await api.search({
        q: q.trim(),
        personId: personId != null ? personId : null,
        from: from.trim() || null,
        to: to.trim() || null,
        platform: platform || null,
        conversationKind: conversationKind || null,
        includeGroups,
        limit: 50,
      });
      empty = hits.length === 0;
    } catch (e) {
      onError(e);
    } finally {
      searching = false;
    }
  }

  async function toggle(id: number) {
    if (expanded === id) {
      expanded = null;
      body = "";
      return;
    }
    try {
      body = await api.searchBody(id);
      expanded = id;
    } catch (e) {
      onError(e);
    }
  }
</script>

<ScrollArea class="p-4">
  <h1 class="mb-3 text-xl font-semibold tracking-tight">Search</h1>
  <form
    class="mb-4 grid gap-3 sm:grid-cols-2"
    onsubmit={(e) => {
      e.preventDefault();
      run();
    }}
  >
    <div class="space-y-1.5 sm:col-span-2">
      <Label for="q">Query</Label>
      <Input id="q" bind:value={q} placeholder="FTS — same as CLI search" />
    </div>
    <div class="space-y-1.5" data-person-picker>
      <Label for="sp">Person</Label>
      <div class="relative">
        <Input
          id="sp"
          bind:value={personFilter}
          placeholder="Messages with…"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={personListOpen}
          aria-controls="person-options"
          autocomplete="off"
          class={personId != null ? "pr-14" : undefined}
          oninput={onPersonFilterInput}
          onfocus={() => (personListOpen = true)}
          onkeydown={onPersonKeydown}
        />
        {#if personId != null}
          <button
            type="button"
            class="absolute top-1/2 right-2 -translate-y-1/2 text-xs text-muted-foreground underline"
            onclick={clearPerson}
          >
            Clear
          </button>
        {/if}
        {#if personListOpen && personFilter.trim() && filteredPeople.length > 0 && personId == null}
          <ul
            id="person-options"
            role="listbox"
            class="person-options absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-md border border-border bg-background py-1 shadow-md"
            onmousedown={(e) => e.preventDefault()}
          >
            {#each filteredPeople as p, i}
              <li>
                <button
                  type="button"
                  role="option"
                  aria-selected={i === personHighlight}
                  class="w-full px-3 py-1.5 text-left text-sm hover:bg-accent {i === personHighlight
                    ? 'bg-accent'
                    : ''}"
                  onclick={() => pickPerson(p)}
                >
                  {p.display_name}{#if p.is_self}
                    {" "}(self){/if}
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
      {#if personId != null}
        <p class="text-xs text-muted-foreground">Messages with {personFilter}</p>
      {/if}
    </div>
    <div class="space-y-1.5">
      <Label for="plat">Platform</Label>
      <select
        id="plat"
        bind:value={platform}
        class="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
      >
        <option value="">Any</option>
        <option value="whatsapp">WhatsApp</option>
        <option value="gmail">Gmail</option>
        <option value="contacts">Contacts</option>
      </select>
    </div>
    <div class="space-y-1.5">
      <Label for="skind">Kind</Label>
      <select
        id="skind"
        bind:value={conversationKind}
        class="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
      >
        <option value="">Any</option>
        <option value="dm">DM</option>
        <option value="group">Group</option>
        <option value="email_thread">Email thread</option>
      </select>
    </div>
    <div class="space-y-1.5">
      <Label for="from">From (ISO date)</Label>
      <Input id="from" bind:value={from} placeholder="2024-01-01" />
    </div>
    <div class="space-y-1.5">
      <Label for="to">To (ISO date)</Label>
      <Input id="to" bind:value={to} placeholder="2026-12-31" />
    </div>
    <label class="flex items-center gap-2 text-sm sm:col-span-2">
      <input type="checkbox" bind:checked={includeGroups} />
      include groups
    </label>
    <Button type="submit" disabled={searching}>{searching ? "Searching…" : "Search"}</Button>
  </form>

  {#if searching}
    <p class="text-sm text-muted-foreground">Searching…</p>
  {:else if !searched}
    <EmptyState
      title="Type a query"
      body="Same full-text search as the CLI. Group chats stay hidden until you tick include groups."
    />
  {:else if empty}
    <EmptyState
      title="No hits"
      body="Try another token, widen the date range, or enable include groups if the match is only in a group."
    />
  {/if}

  <ol class="divide-y divide-border">
    {#each hits as h}
      <li class="px-1 py-2">
        <button type="button" class="w-full text-left hover:bg-accent" onclick={() => toggle(h.message_id)}>
          <div class="text-xs text-muted-foreground">
            {[h.sent_at || "no date", h.platform, h.conversation_kind, h.person_name || "", h.conversation_title || ""]
              .filter(Boolean)
              .join(" · ")}
          </div>
          <p class="mt-1 whitespace-pre-wrap text-sm">{(h.snippet || h.subject || "").replace(/<attached:\s*[^>]+>/gi, "").trim()}</p>
        </button>
        <CasAttach items={h.attachments || []} />
        {#if expanded === h.message_id}
          <p class="bg-muted px-2 py-2 text-sm whitespace-pre-wrap">{body}</p>
        {/if}
      </li>
    {/each}
  </ol>
</ScrollArea>
