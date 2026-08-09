<script lang="ts">
  import { onMount } from "svelte";
  import { api, type ReviewRow, type ReviewShow } from "./api";
  import { Button } from "$lib/components/ui/button/index.js";
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import ConfirmDialog from "./ConfirmDialog.svelte";
  import EmptyState from "./EmptyState.svelte";

  let {
    onError,
    onChanged,
  }: { onError: (e: unknown) => void; onChanged: () => Promise<void> } = $props();

  let rows = $state<ReviewRow[]>([]);
  let detail = $state<ReviewShow | null>(null);
  let confirmOpen = $state(false);
  let confirmTitle = $state("");
  let confirmDesc = $state("");
  let confirmRun = $state<(() => Promise<void>) | null>(null);
  let loading = $state(true);

  async function reload() {
    loading = true;
    try {
      rows = await api.reviewList();
      if (detail) {
        const still = rows.find((r) => r.id === detail?.review.id);
        detail = still ? await api.reviewShow(still.id) : null;
      }
    } catch (e) {
      onError(e);
    } finally {
      loading = false;
    }
  }

  async function openRow(id: number) {
    try {
      detail = await api.reviewShow(id);
    } catch (e) {
      onError(e);
    }
  }

  function ask(title: string, description: string, run: () => Promise<void>) {
    confirmTitle = title;
    confirmDesc = description;
    confirmRun = run;
    confirmOpen = true;
  }

  function accept() {
    if (!detail) return;
    const id = detail.review.id;
    ask(`Accept review ${id}?`, "Links the name-only identity onto the suggested person. Messages stay put.", async () => {
      await api.reviewAccept(id);
      await onChanged();
      await reload();
    });
  }

  function reject() {
    if (!detail) return;
    const id = detail.review.id;
    ask(`Reject review ${id}?`, "This pair will not be suggested again.", async () => {
      await api.reviewReject(id);
      await onChanged();
      await reload();
    });
  }

  onMount(() => {
    reload();
  });
</script>

<ScrollArea class="p-4">
  <h1 class="mb-3 text-xl font-semibold tracking-tight">Review</h1>
  {#if loading}
    <p class="text-sm text-muted-foreground">Loading review queue…</p>
  {:else if rows.length === 0}
    <EmptyState
      title="Nothing to review"
      body="Name-only WhatsApp matches show up here. They never auto-merge. Import Contacts if you expect a queue."
    />
  {:else}
    <ul class="mb-4 space-y-1">
      {#each rows as r}
        <li>
          <button
            type="button"
            class="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent {detail?.review.id === r.id
              ? 'bg-accent'
              : ''}"
            onclick={() => openRow(r.id)}
          >
            #{r.id} · {r.left_name} → {r.right_name || `person ${r.right_person_id ?? "?"}`}
            <span class="text-muted-foreground"> ({r.score.toFixed(2)})</span>
          </button>
        </li>
      {/each}
    </ul>
  {/if}

  {#if detail}
    <div class="space-y-3 border-t border-border pt-3">
      <p class="text-sm">{detail.review.reason}</p>
      <p class="text-sm">
        Left identity {detail.review.left_identity_id} ({detail.review.left_name}) → person
        {detail.review.right_person_id ?? "—"} ({detail.review.right_name || "—"})
      </p>
      <ul class="space-y-1 text-xs text-muted-foreground">
        {#each detail.evidence as e}
          <li>{e.type} · {e.score} · {e.detail}</li>
        {/each}
      </ul>
      <div>
        <p class="mb-1 text-xs font-medium">Sample messages</p>
        {#each detail.samples as s}
          <p class="mb-2 whitespace-pre-wrap text-sm">{s.sent_at || "no date"} · {s.body_text}</p>
        {/each}
        {#if detail.samples.length === 0}
          <p class="text-sm text-muted-foreground">No sample messages.</p>
        {/if}
      </div>
      <div class="flex gap-2">
        <Button onclick={accept}>Accept</Button>
        <Button variant="outline" onclick={reject}>Reject</Button>
      </div>
    </div>
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
