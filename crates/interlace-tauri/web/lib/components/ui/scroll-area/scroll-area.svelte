<script lang="ts">
  import type { HTMLAttributes } from "svelte/elements";
  import type { Snippet } from "svelte";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    children,
    ...rest
  }: HTMLAttributes<HTMLDivElement> & { children?: Snippet } = $props();
</script>

<!-- Vertical scroll only — long labels/timestamps must not pan sideways. -->
<div class={cn("min-h-0 overflow-x-hidden overflow-y-auto", className)} {...rest}>
  {@render children?.()}
</div>
