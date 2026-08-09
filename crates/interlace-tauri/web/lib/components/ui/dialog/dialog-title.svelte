<script lang="ts">
  import { Dialog as DialogPrimitive } from "bits-ui";
  import type { Snippet } from "svelte";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    children,
    ...rest
  }: DialogPrimitive.TitleProps & { children?: Snippet } = $props();
</script>

<DialogPrimitive.Title class={cn("text-lg leading-none font-semibold", className)} {...rest}>
  {@render children?.()}
</DialogPrimitive.Title>
