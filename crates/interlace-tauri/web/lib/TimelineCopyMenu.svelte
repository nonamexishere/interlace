<script lang="ts">
  import { t } from "$lib/i18n";

  let {
    x,
    y,
    n = 1,
    mail = false,
    hash = null as string | null,
    onCopy,
    onSearch,
    onSearchThisConversation,
    onOpenOriginal,
  }: {
    x: number;
    y: number;
    n?: number;
    mail?: boolean;
    hash?: string | null;
    onCopy: () => void;
    onSearch: () => void;
    onSearchThisConversation: () => void;
    onOpenOriginal: () => void;
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
    onclick={onCopy}>{n > 1 ? t("copyN").replace("{n}", String(n)) : t("copyText")}</button>
  <button
    type="button"
    class="block w-full px-3 py-1.5 text-left text-sm hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
    role="menuitem"
    onclick={onSearch}>{t("search")}</button>
  <button
    type="button"
    class="block w-full px-3 py-1.5 text-left text-sm hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
    role="menuitem"
    onclick={onSearchThisConversation}>{t("searchThisConversation")}</button>
  {#if mail && n <= 1}
    {#if hash}
      <button
        type="button"
        class="block w-full px-3 py-1.5 text-left text-sm hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
        role="menuitem"
        onclick={onOpenOriginal}>{t("openOriginal")}</button>
    {:else}
      <button
        type="button"
        class="block w-full px-3 py-1.5 text-left text-sm text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
        role="menuitem"
        disabled>{t("openOriginalMissing")}</button>
    {/if}
  {/if}
</div>
