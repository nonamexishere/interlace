<script lang="ts">
  import type { UrlSegment } from "./linkify";
  import { splitFind } from "./findHighlight";

  let {
    text,
    splitUrls,
    openUrl,
    findQ = "",
  }: {
    text: string;
    splitUrls: (raw: string) => UrlSegment[];
    openUrl: (url: string) => void;
    findQ?: string;
  } = $props();

  const segments: UrlSegment[] = $derived(splitUrls(text));
</script>

{#each segments as seg}
  {#if seg.kind === "url"}
    <a
      href={seg.text}
      data-bubble-link
      class="break-all underline text-foreground"
      onclick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        openUrl(seg.text);
      }}>{#each splitFind(seg.text, findQ) as part}{#if part.kind === "mark"}<mark class="search-mark">{part.text}</mark>{:else}{part.text}{/if}{/each}</a>
  {:else}
    {#each splitFind(seg.text, findQ) as part}
      {#if part.kind === "mark"}
        <mark class="search-mark">{part.text}</mark>
      {:else}
        {part.text}
      {/if}
    {/each}
  {/if}
{/each}
