<script lang="ts">
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import { Button } from "$lib/components/ui/button/index.js";

  let {
    open = $bindable(false),
    title,
    description,
    confirmLabel = "Confirm",
    onconfirm,
  }: {
    open?: boolean;
    title: string;
    description: string;
    confirmLabel?: string;
    onconfirm: () => void | Promise<void>;
  } = $props();

  let busy = $state(false);

  async function go() {
    busy = true;
    open = false;
    try {
      await onconfirm();
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
      <Dialog.Description>{description}</Dialog.Description>
    </Dialog.Header>
    <Dialog.Footer>
      <Button variant="outline" disabled={busy} onclick={cancel}>Cancel</Button>
      <Button disabled={busy} onclick={go}>{confirmLabel}</Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
