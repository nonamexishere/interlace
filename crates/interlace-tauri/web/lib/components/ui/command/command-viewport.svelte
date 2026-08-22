<script lang="ts">
  import { Command as CommandPrimitive } from "bits-ui";
  import type { Snippet } from "svelte";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    children,
    ...rest
  }: CommandPrimitive.ViewportProps & { children?: Snippet } = $props();
</script>

<CommandPrimitive.Viewport
  class={cn("max-h-72 overflow-y-auto overflow-x-hidden p-1", className)}
  {...rest}
>
  {@render children?.()}
</CommandPrimitive.Viewport>
