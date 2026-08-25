<script lang="ts">
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import { Button } from "$lib/components/ui/button/index.js";

  let {
    open = $bindable(false),
    title,
    description,
    confirmLabel = "Confirm",
    onconfirm,
    onerror,
  }: {
    open?: boolean;
    title: string;
    description: string;
    confirmLabel?: string;
    onconfirm: () => void | Promise<void>;
    onerror?: (e: unknown) => void;
  } = $props();

  let busy = $state(false);

  $effect.pre(() => {
    if (busy && open) {
      open = false;
    }
  });

  async function go() {
    busy = true;
    open = false;
    try {
      await onconfirm();
    } catch (e) {
      onerror?.(e);
    } finally {
      busy = false;
    }
  }

  function cancel() {
    open = false;
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Content>
    <Dialog.Header>
      <Dialog.Title>{title}</Dialog.Title>
      <Dialog.Description class="break-all">{description}</Dialog.Description>
    </Dialog.Header>
    <Dialog.Footer>
      <Button variant="outline" onclick={cancel}>Cancel</Button>
      <Button disabled={busy} onclick={go}>{confirmLabel}</Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
