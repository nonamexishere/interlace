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
  let personId = $state("");
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

  async function run() {
    empty = false;
    searched = true;
    searching = true;
    expanded = null;
    body = "";
    try {
      hits = await api.search({
        q: q.trim(),
        personId: personId ? Number(personId) : null,
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
    <div class="space-y-1.5">
      <Label for="sp">Person id</Label>
      <Input id="sp" bind:value={personId} placeholder="optional" list="people-ids" />
      <datalist id="people-ids">
        {#each people as p}
          <option value={String(p.id)}>{p.display_name}</option>
        {/each}
      </datalist>
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
