<script lang="ts">
  import Inbox from "@lucide/svelte/icons/inbox";
  import { Button } from "$lib/components/ui/button/index.js";

  let {
    title,
    body,
    actionLabel,
    onAction,
  }: {
    title: string;
    body: string;
    actionLabel?: string;
    onAction?: () => void;
  } = $props();
</script>

<div class="rounded-md border border-border bg-muted/40 px-4 py-6 text-sm" data-empty>
  <Inbox class="size-5 text-muted-foreground" />
  <p class="mt-2 font-medium">{title}</p>
  <p class="mt-1 text-muted-foreground">{body}</p>
  {#if actionLabel}
    <Button size="sm" class="mt-3" onclick={() => onAction?.()}>{actionLabel}</Button>
  {/if}
</div>
