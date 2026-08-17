<script lang="ts">
  import Inbox from "@lucide/svelte/icons/inbox";

  let { title, body }: { title: string; body: string } = $props();
</script>

<div class="rounded-md border border-border bg-muted/40 px-4 py-6 text-sm" data-empty>
  <Inbox class="size-5 text-muted-foreground" />
  <p class="mt-2 font-medium">{title}</p>
  <p class="mt-1 text-muted-foreground">{body}</p>
</div>
