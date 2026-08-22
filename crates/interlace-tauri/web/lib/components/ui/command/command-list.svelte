<script lang="ts">
  import { Command as CommandPrimitive } from "bits-ui";
  import type { Snippet } from "svelte";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    children,
    ...rest
  }: CommandPrimitive.ListProps & { children?: Snippet } = $props();
</script>

<CommandPrimitive.List
  class={cn("max-h-72 overflow-hidden", className)}
  {...rest}
>
  {@render children?.()}
</CommandPrimitive.List>
