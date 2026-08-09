<script lang="ts">
  import { Dialog as DialogPrimitive } from "bits-ui";
  import type { Snippet } from "svelte";

  let {
    open = $bindable(false),
    children,
    ...rest
  }: DialogPrimitive.RootProps & { children?: Snippet } = $props();
</script>

<DialogPrimitive.Root bind:open {...rest}>
  {@render children?.()}
</DialogPrimitive.Root>
