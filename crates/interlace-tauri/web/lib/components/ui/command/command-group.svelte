<script lang="ts">
  import { Command as CommandPrimitive } from "bits-ui";
  import type { Snippet } from "svelte";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    children,
    ...rest
  }: CommandPrimitive.GroupProps & { children?: Snippet } = $props();
</script>

<CommandPrimitive.Group
  class={cn("overflow-hidden p-1 text-foreground", className)}
  {...rest}
>
  {@render children?.()}
</CommandPrimitive.Group>
