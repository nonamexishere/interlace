<script lang="ts">
  import { t } from "$lib/i18n";

  let {
    x,
    y,
    onCopy,
    onSearch,
  }: {
    x: number;
    y: number;
    onCopy: () => void;
    onSearch: () => void;
  } = $props();
</script>

<div
  class="fixed z-[80] min-w-32 rounded-md border border-border bg-background py-1 shadow-md"
  style="left: {x}px; top: {y}px"
  data-copy-menu
  data-context-menu
  role="menu"
>
  <button
    type="button"
    class="block w-full px-3 py-1.5 text-left text-sm hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
    role="menuitem"
    onclick={onCopy}>{t("copyText")}</button
  >
  <button
    type="button"
    class="block w-full px-3 py-1.5 text-left text-sm hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
    role="menuitem"
    onclick={onSearch}>{t("search")}</button
  >
</div>
