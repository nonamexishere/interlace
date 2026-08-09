<script lang="ts">
  let { title, body }: { title: string; body: string } = $props();
</script>

<div class="rounded-md border border-border bg-muted/40 px-4 py-6 text-sm" data-empty>
  <p class="font-medium">{title}</p>
  <p class="mt-1 text-muted-foreground">{body}</p>
</div>
