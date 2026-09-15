<script module lang="ts">
  const urlByHash = new Map<string, string>();
</script>

<script lang="ts">
  import User from "@lucide/svelte/icons/user";
  import { api } from "./api";

  let {
    personId,
    display_name,
    photo_cas_hash = null,
  }: {
    personId: number;
    display_name: string;
    photo_cas_hash?: string | null;
  } = $props();

  let src = $state<string | null>(null);
  let failed = $state(false);

  function unitsOf(s: string): string[] {
    if (typeof Intl !== "undefined" && "Segmenter" in Intl) {
      const seg = new Intl.Segmenter(undefined, { granularity: "grapheme" });
      return Array.from(seg.segment(s), (part) => part.segment);
    }
    return Array.from(s);
  }

  function firstUnit(s: string): string {
    return unitsOf(s)[0] ?? "";
  }

  function initialsFrom(name: string): string {
    const n = name.trim();
    if (!n) return "";
    const words = n.split(/\s+/);
    if (words.length >= 2) {
      return (firstUnit(words[0]) + firstUnit(words[1])).toLocaleUpperCase();
    }
    const word = words[0] ?? "";
    const units = unitsOf(word);
    if (word.length === 1 || units.length === 1) {
      return (units[0] ?? word).toLocaleUpperCase();
    }
    return word.slice(0, 2).toLocaleUpperCase();
  }

  const letters = $derived(initialsFrom(display_name ?? ""));

  $effect(() => {
    const hash = (photo_cas_hash ?? "").trim();
    failed = false;
    src = null;
    if (!hash) return;
    const cached = urlByHash.get(hash);
    if (cached) {
      src = cached;
      return;
    }
    let cancelled = false;
    api
      .casDataUrl(hash)
      .then((url) => {
        urlByHash.set(hash, url);
        if (!cancelled) src = url;
      })
      .catch(() => {
        if (!cancelled) failed = true;
      });
    return () => {
      cancelled = true;
    };
  });

  function onImgError() {
    src = null;
    failed = true;
  }
</script>

<div
  class="flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-md bg-muted text-xs font-medium text-muted-foreground"
  aria-hidden="true"
>
  {#key personId + (photo_cas_hash ?? "")}
    {#if src && !failed}
      <img
        src={src}
        alt=""
        class="size-8 object-cover"
        onerror={onImgError}
      />
    {:else if letters}
      <span>{letters}</span>
    {:else}
      <User class="size-4" />
    {/if}
  {/key}
</div>
