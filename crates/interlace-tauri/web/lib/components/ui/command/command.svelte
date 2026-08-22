<script lang="ts">
  import { Command as CommandPrimitive } from "bits-ui";
  import type { Snippet } from "svelte";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    value = $bindable(""),
    vimBindings = false,
    children,
    ...rest
  }: CommandPrimitive.RootProps & { children?: Snippet } = $props();
</script>

<CommandPrimitive.Root
  bind:value
  {vimBindings}
  class={cn(
    "flex h-full w-full flex-col overflow-hidden rounded-md bg-background text-foreground",
    className,
  )}
  {...rest}
>
  {@render children?.()}
</CommandPrimitive.Root>
