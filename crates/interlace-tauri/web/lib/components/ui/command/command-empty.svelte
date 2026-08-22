<script lang="ts">
  import { Command as CommandPrimitive } from "bits-ui";
  import type { Snippet } from "svelte";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    children,
    ...rest
  }: CommandPrimitive.EmptyProps & { children?: Snippet } = $props();
</script>

<CommandPrimitive.Empty
  class={cn("py-6 text-center text-sm text-muted-foreground", className)}
  {...rest}
>
  {@render children?.()}
</CommandPrimitive.Empty>
