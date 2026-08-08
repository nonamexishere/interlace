<script lang="ts">
  import type { HTMLLabelAttributes } from "svelte/elements";
  import type { Snippet } from "svelte";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    children,
    ...rest
  }: HTMLLabelAttributes & { children?: Snippet } = $props();
</script>

<label class={cn("text-sm leading-none font-medium", className)} {...rest}>
  {@render children?.()}
</label>
