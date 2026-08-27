<script lang="ts">
  import type { Person } from "./api";
  import { mergeTargets } from "./utils";
  import { humanTime } from "./formatTime";
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Label } from "$lib/components/ui/label/index.js";
  import EmptyState from "$lib/EmptyState.svelte";

  let {
    open = $bindable(false),
    people,
    keepId,
    keepName,
    personLabel,
    onPick,
  }: {
    open?: boolean;
    people: Person[];
    keepId: number | null;
    keepName: string;
    personLabel: (p: { display_name: string; is_self: boolean }) => string;
    onPick: (other: Person) => void;
  } = $props();

  let mergeQuery = $state("");
  let allowSelf = $state(false);
  const mergeList = $derived(
    keepId == null ? [] : mergeTargets(people, keepId, allowSelf, mergeQuery),
  );

  $effect(() => {
    if (open) {
      mergeQuery = "";
      allowSelf = false;
    }
  });
</script>

<Dialog.Root bind:open>
  <Dialog.Content>
    <Dialog.Header>
      <Dialog.Title>Merge into {keepName}</Dialog.Title>
      <Dialog.Description>
        Pick a person by name. {keepName} is kept. Names never auto-merge.
      </Dialog.Description>
    </Dialog.Header>
    <div class="space-y-1.5">
      <Label for="merge-query">Search</Label>
      <Input id="merge-query" type="search" bind:value={mergeQuery} placeholder="name" />
    </div>
    <label class="flex items-center gap-2 text-sm">
      <input type="checkbox" class="focus-visible:ring-2 focus-visible:ring-ring" bind:checked={allowSelf} />
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
              class="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring {p.is_self
                ? 'font-semibold'
                : ''}"
              onclick={() => onPick(p)}
            >
              <span>{personLabel(p)}</span>
              {#if p.last_activity_at || p.preview}
                <span class="chrome-preview-fg mt-0.5 block truncate text-xs font-normal text-muted-foreground">
                  {humanTime(p.last_activity_at)}{p.last_activity_at && p.preview ? " · " : ""}{p.preview ?? ""}
                </span>
              {/if}
            </button>
          </li>
        {/each}
      </ul>
    {/if}
    <Dialog.Footer>
      <Button variant="outline" onclick={() => (open = false)}>Cancel</Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
