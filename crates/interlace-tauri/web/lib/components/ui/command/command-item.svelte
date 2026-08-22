<script lang="ts">
  import { Command as CommandPrimitive } from "bits-ui";
  import type { Snippet } from "svelte";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    children,
    ...rest
  }: CommandPrimitive.ItemProps & { children?: Snippet } = $props();
</script>

<CommandPrimitive.Item
  class={cn(
    "relative flex cursor-default items-center rounded-md px-2 py-1.5 text-sm outline-none select-none data-selected:bg-accent data-selected:text-accent-foreground data-disabled:pointer-events-none data-disabled:opacity-50",
    className,
  )}
  {...rest}
>
  {@render children?.()}
</CommandPrimitive.Item>
