<script lang="ts">
  import { Tooltip as TooltipPrimitive } from "bits-ui";
  import type { Snippet } from "svelte";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    sideOffset = 4,
    children,
    ...rest
  }: TooltipPrimitive.ContentProps & { children?: Snippet } = $props();
</script>

<TooltipPrimitive.Portal>
  <TooltipPrimitive.Content
    {sideOffset}
    class={cn(
      "z-50 overflow-hidden rounded-md border border-border bg-background px-3 py-1.5 text-xs text-foreground shadow-md",
      className,
    )}
    {...rest}
  >
    {@render children?.()}
  </TooltipPrimitive.Content>
</TooltipPrimitive.Portal>
