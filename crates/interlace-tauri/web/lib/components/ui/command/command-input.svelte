<script lang="ts">
  import { Command as CommandPrimitive } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    value = $bindable(""),
    ...rest
  }: CommandPrimitive.InputProps = $props();
</script>

<CommandPrimitive.Input
  bind:value
  class={cn(
    "flex h-10 w-full border-b border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
    className,
  )}
  {...rest}
/>
