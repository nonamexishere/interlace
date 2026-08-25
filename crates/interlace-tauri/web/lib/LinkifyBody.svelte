<script lang="ts">
  import type { UrlSegment } from "./linkify";

  let {
    text,
    splitUrls,
    openUrl,
  }: {
    text: string;
    splitUrls: (raw: string) => UrlSegment[];
    openUrl: (url: string) => void;
  } = $props();

  const segments: UrlSegment[] = $derived(splitUrls(text));
</script>

{#each segments as seg}
  {#if seg.kind === "url"}
    <a
      href={seg.text}
      data-bubble-link
      class="break-words underline text-foreground"
      onclick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        openUrl(seg.text);
      }}>{seg.text}</a>
  {:else}
    {seg.text}
  {/if}
{/each}
