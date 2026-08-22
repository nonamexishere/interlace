<script lang="ts">
  import { Command as CommandPrimitive } from "bits-ui";
  import type { Snippet } from "svelte";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    children,
    ...rest
  }: CommandPrimitive.GroupHeadingProps & { children?: Snippet } = $props();
</script>

<CommandPrimitive.GroupHeading
  class={cn("px-2 py-1.5 text-xs font-medium text-muted-foreground", className)}
  {...rest}
>
  {@render children?.()}
</CommandPrimitive.GroupHeading>
