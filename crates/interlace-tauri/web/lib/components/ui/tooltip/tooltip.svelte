<script lang="ts">
  import { Tooltip as TooltipPrimitive } from "bits-ui";
  import type { Snippet } from "svelte";

  let {
    open = $bindable(false),
    children,
    ...rest
  }: TooltipPrimitive.RootProps & { children?: Snippet } = $props();
</script>

<TooltipPrimitive.Root bind:open {...rest}>
  {@render children?.()}
</TooltipPrimitive.Root>
