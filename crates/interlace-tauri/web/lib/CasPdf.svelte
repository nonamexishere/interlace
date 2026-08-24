<script lang="ts">
  let {
    srcs,
    srcKey,
    filename,
    onBroken,
  }: {
    srcs: Record<string, string>;
    srcKey: string;
    filename?: string | null;
    onBroken?: () => void;
  } = $props();
</script>

<div
  class="overflow-hidden rounded-md border border-border bg-background"
  data-cas-pdf
>
  <iframe
    src={srcs[srcKey]}
    title={filename || "PDF"}
    class="h-64 w-full max-w-md bg-background"
    onerror={() => onBroken?.()}
  ></iframe>
</div>
