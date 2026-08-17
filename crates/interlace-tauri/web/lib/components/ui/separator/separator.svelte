<script lang="ts">
  import { Separator as SeparatorPrimitive } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    orientation = "horizontal",
    decorative = true,
    ...rest
  }: SeparatorPrimitive.RootProps = $props();
</script>

<SeparatorPrimitive.Root
  {orientation}
  {decorative}
  class={cn(
    "shrink-0 bg-border",
    orientation === "horizontal" ? "h-px w-full" : "h-full w-px",
    className,
  )}
  {...rest}
/>
