<script lang="ts">
  import { onMount } from "svelte";
  import { api, type LinkEvent, type ReviewPanel, type ReviewRow, type ReviewShow } from "./api";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Card } from "$lib/components/ui/card/index.js";
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import { Separator } from "$lib/components/ui/separator/index.js";
  import ConfirmDialog from "./ConfirmDialog.svelte";
  import EmptyState from "./EmptyState.svelte";

  let {
    onError,
    onChanged,
    onGoImport,
  }: {
    onError: (e: unknown) => void;
    onChanged: () => Promise<void>;
    onGoImport: () => void;
  } = $props();

  let rows = $state<ReviewRow[]>([]);
  let events = $state<LinkEvent[]>([]);
  let detail = $state<ReviewShow | null>(null);
  let confirmOpen = $state(false);
  let confirmTitle = $state("");
  let confirmDesc = $state("");
  let confirmRun = $state<(() => Promise<void>) | null>(null);
  let loading = $state(true);
  let undoing = $state(false);
  let resolving = $state(false);
  let selected = $state<number[]>([]);

  const UNDOABLE = new Set(["merge_persons", "link", "unlink"]);

  const lastUndoable = $derived.by(() => {
    const undone = new Set(
      events
        .filter((e) => e.op === "split_person" && e.undo_of != null)
        .map((e) => e.undo_of as number),
    );
    return (
      events.find(
        (e) => UNDOABLE.has(e.op) && e.actor === "user" && !undone.has(e.id),
      ) ?? null
    );
  });

  function panelsOf(shown: ReviewShow): ReviewPanel[] {
    return shown.sides && shown.sides.length > 0 ? shown.sides : [shown.left, shown.right];
  }

  function applyDetail(shown: ReviewShow | null) {
    detail = shown;
    selected = shown
      ? panelsOf(shown)
          .map((p) => p.person_id)
          .filter((id): id is number => id != null)
      : [];
  }

  async function reload() {
    loading = true;
    try {
      rows = await api.reviewList();
      events = await api.linkEvents();
      if (detail) {
        const still = rows.find((r) => r.id === detail?.review.id);
        applyDetail(still ? await api.reviewShow(still.id) : null);
      }
    } catch (e) {
      onError(e);
    } finally {
      loading = false;
    }
  }

  async function openRow(id: number) {
    try {
      applyDetail(await api.reviewShow(id));
    } catch (e) {
      onError(e);
    }
  }

  function ask(title: string, description: string, run: () => Promise<void>) {
    if (resolving || undoing) return;
    confirmTitle = title;
    confirmDesc = description;
    confirmRun = run;
    confirmOpen = true;
  }

  function canAccept(): boolean {
    if (!detail) return false;
    if (selected.length >= 2) return true;
    // I3 / unlinked left: link onto one checked person.
    return detail.left.person_id == null && selected.length >= 1;
  }

  function accept() {
    if (resolving || undoing || !detail || !canAccept()) return;
    const id = detail.review.id;
    const ids = [...selected];
    const n = ids.length;
    ask("Link these people?", `Merge ${n} people into one. Messages stay put.`, async () => {
      resolving = true;
      try {
        await api.reviewAccept(id, ids);
        await reload();
        void onChanged();
      } catch (e) {
        onError(e);
      } finally {
        resolving = false;
      }
    });
  }

  function toggle(pid: number, on: boolean) {
    if (on) {
      if (!selected.includes(pid)) selected = [...selected, pid];
    } else {
      selected = selected.filter((x) => x !== pid);
    }
  }

  function selectAll() {
    if (!detail) return;
    selected = panelsOf(detail)
      .map((p) => p.person_id)
      .filter((id): id is number => id != null);
  }

  function selectNone() {
    selected = [];
  }

  function reject() {
    if (resolving || undoing || !detail) return;
    const id = detail.review.id;
    ask("Stop suggesting this pair?", "These people will not be suggested again.", async () => {
      resolving = true;
      try {
        await api.reviewReject(id);
        await reload();
        void onChanged();
      } catch (e) {
        onError(e);
      } finally {
        resolving = false;
      }
    });
  }

  function requestUndo() {
    const ev = lastUndoable;
    if (!ev || undoing) return;
    const id = ev.id;
    ask("Undo last link?", "Reverses the last identity graph change. Messages stay put.", async () => {
      await runUndo(id);
    });
  }

  async function runUndo(id: number) {
    if (undoing) return;
    undoing = true;
    try {
      await api.undo(id);
      await reload();
      // People list refresh holds the archive lock; do not block Review on it.
      void onChanged();
    } catch (e) {
      onError(e);
    } finally {
      undoing = false;
    }
  }

  onMount(() => {
    reload();
  });

  function platformLabel(p: string): string {
    switch (p) {
      case "whatsapp":
        return "WhatsApp";
      case "gmail":
        return "Gmail";
      case "contacts":
        return "Contacts";
      case "owner":
        return "Me";
      default:
        return p;
    }
  }

  function panelTitle(panel: { display_name: string | null; platforms?: string[] }): string {
    const name = panel.display_name || "—";
    const plats = (panel.platforms ?? []).map(platformLabel).filter(Boolean);
    if (plats.length) return `${name} (${plats.join(", ")})`;
    return `${name} (No source)`;
  }

  function identifierLabel(id: { kind: string; value_normalized: string }): string {
    return `${id.kind}: ${id.value_normalized}`;
  }

  function countLabel(n: number): string {
    return n === 1 ? "1 message" : `${n} messages`;
  }
</script>

<ScrollArea class="p-4">
  <h1 class="mb-3 text-xl font-semibold tracking-tight">Review</h1>
  {#if loading}
    <p class="text-sm text-muted-foreground">Loading review queue…</p>
  {:else if rows.length === 0}
    <EmptyState
      title="Nothing to review"
      body="Name-only WhatsApp matches show up here. They never auto-merge. Import Contacts if you expect a queue."
      actionLabel="Import"
      onAction={onGoImport}
    />
  {:else}
    <ul class="mb-4 space-y-1">
      {#each rows as r}
        <li>
          <button
            type="button"
            class="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring {detail?.review.id === r.id
              ? 'bg-accent'
              : ''}"
            onclick={() => openRow(r.id)}
          >
            {r.left_name} → {r.right_name || "—"}
            <span class="text-muted-foreground"> ({r.score.toFixed(2)})</span>
          </button>
        </li>
      {/each}
    </ul>
  {/if}

  {#if lastUndoable}
    <div class="mb-3">
      <Button
        variant="outline"
        size="sm"
        data-review-undo
        disabled={undoing}
        onclick={requestUndo}
      >
        {undoing ? "Undoing…" : "Undo last link"}
      </Button>
    </div>
  {/if}

  {#if detail}
    <Separator />
    <Card data-review-card class="mt-3 space-y-3 p-3">
      <p class="text-sm">{detail.review.reason}</p>
      <ul class="space-y-1 text-xs text-muted-foreground">
        {#each detail.evidence as e}
          <li>{e.type} · {e.score} · {e.detail}</li>
        {/each}
      </ul>
      <div class="flex flex-wrap gap-2 text-xs">
        <button type="button" class="text-muted-foreground underline focus-visible:ring-2 focus-visible:ring-ring" onclick={selectAll}>Select all</button>
        <button type="button" class="text-muted-foreground underline focus-visible:ring-2 focus-visible:ring-ring" onclick={selectNone}>Select none</button>
      </div>
      <div class="grid grid-cols-2 gap-3">
        {#each panelsOf(detail) as panel}
          <label class="min-w-0 cursor-pointer">
            {#if panel.person_id != null}
              <input
                type="checkbox"
                class="mb-1 mr-1 align-middle focus-visible:ring-2 focus-visible:ring-ring"
                checked={selected.includes(panel.person_id)}
                onchange={(e) => toggle(panel.person_id!, e.currentTarget.checked)}
              />
            {/if}
            <span class="mb-1 text-xs font-medium">{panelTitle(panel)}</span>
            {#if panel.identifiers && panel.identifiers.length > 0}
              <ul class="mb-1 space-y-0.5 text-xs text-muted-foreground">
                {#each panel.identifiers as id}
                  <li>{identifierLabel(id)}</li>
                {/each}
              </ul>
            {/if}
            <p class="mb-1 text-xs text-muted-foreground">{countLabel(panel.message_count)}</p>
            {#if panel.samples.length === 0}
              <p class="text-sm text-muted-foreground">No messages on this side</p>
            {:else}
              {#each panel.samples as s}
                <p class="mb-2 whitespace-pre-wrap text-sm">
                  {s.sent_at || "no date"} · {s.body_text}
                </p>
              {/each}
            {/if}
          </label>
        {/each}
      </div>
      <Separator />
      <p class="text-xs text-muted-foreground">
        Accept links these people and can be undone. Reject only stops suggesting this pair.
      </p>
      <div class="flex gap-2">
        <Button onclick={accept} disabled={resolving || undoing || !canAccept()}>Accept</Button>
        <Button variant="outline" onclick={reject} disabled={resolving || undoing}>Reject</Button>
      </div>
    </Card>
  {/if}
</ScrollArea>

<ConfirmDialog
  bind:open={confirmOpen}
  title={confirmTitle}
  description={confirmDesc}
  onconfirm={async () => {
    if (confirmRun) await confirmRun();
  }}
/>
