<script lang="ts">
  import type { HTMLAttributes } from "svelte/elements";
  import type { Snippet } from "svelte";
  import { fade } from "svelte/transition";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    message = "",
    children,
    ...rest
  }: HTMLAttributes<HTMLDivElement> & {
    message?: string;
    children?: Snippet;
  } = $props();
</script>

<div
  data-toast
  role="status"
  transition:fade={{ duration: 180 }}
  class={cn(
    "rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground shadow-md",
    className,
  )}
  {...rest}
>
  {#if message}
    {message}
  {:else}
    {@render children?.()}
  {/if}
</div>
