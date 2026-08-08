<script lang="ts">
  import { Dialog as DialogPrimitive } from "bits-ui";
  import X from "@lucide/svelte/icons/x";
  import type { Snippet } from "svelte";
  import { cn } from "$lib/utils.js";

  let {
    class: className,
    children,
    ...rest
  }: DialogPrimitive.ContentProps & { children?: Snippet } = $props();
</script>

<DialogPrimitive.Portal>
  <DialogPrimitive.Overlay
    class="fixed inset-0 z-50 bg-black/50"
  />
  <DialogPrimitive.Content
    class={cn(
      "fixed top-1/2 left-1/2 z-50 grid w-full max-w-md -translate-x-1/2 -translate-y-1/2 gap-4 rounded-lg border border-border bg-background p-6 shadow-lg",
      className,
    )}
    {...rest}
  >
    {@render children?.()}
    <DialogPrimitive.Close
      class="absolute top-3 right-3 inline-flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent"
    >
      <X class="size-4" />
      <span class="sr-only">Close</span>
    </DialogPrimitive.Close>
  </DialogPrimitive.Content>
</DialogPrimitive.Portal>
