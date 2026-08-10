<script lang="ts">
  import { api } from "./api";

  export type Attachment = {
    id: number;
    cas_hash?: string | null;
    filename?: string | null;
    mime?: string | null;
    kind: string;
    omitted: boolean;
    missing: boolean;
  };

  let { items }: { items: Attachment[] } = $props();

  function isImage(a: Attachment) {
    const m = (a.mime || "").toLowerCase();
    const n = (a.filename || "").toLowerCase();
    return (
      a.kind === "image" ||
      a.kind === "sticker" ||
      m.startsWith("image/") ||
      /\.(jpe?g|png|gif|webp|bmp)$/.test(n)
    );
  }

  function isAudio(a: Attachment) {
    const m = (a.mime || "").toLowerCase();
    const n = (a.filename || "").toLowerCase();
    return a.kind === "voice" || m.startsWith("audio/") || /\.(opus|ogg|mp3|m4a|aac|wav)$/.test(n);
  }

  let srcs = $state<Record<string, string>>({});
  let broken = $state<Record<string, boolean>>({});
  const requested = new Set<string>();

  function hashOf(a: Attachment): string | null {
    const h = a.cas_hash ?? (a as { casHash?: string | null }).casHash;
    return h || null;
  }

  function keyOf(a: Attachment): string {
    return hashOf(a) || a.filename || String(a.id);
  }

  $effect(() => {
    for (const a of items || []) {
      const hash = hashOf(a);
      const k = keyOf(a);
      if (!hash || requested.has(k)) continue;
      requested.add(k);
      api
        .casDataUrl(hash)
        .then((url) => {
          srcs = { ...srcs, [k]: url };
        })
        .catch(() => {
          broken = { ...broken, [k]: true };
        });
    }
  });
</script>

{#if items?.length}
  <ul class="mt-2 space-y-2">
    {#each items as a}
      <li>
        {#if a.omitted}
          <p class="text-xs text-muted-foreground">Media omitted in this export</p>
        {:else if a.missing || !hashOf(a)}
          <p class="text-xs text-muted-foreground">
            Photo/file not stored ({a.filename || "attachment"}). Re-import the WhatsApp ZIP from the
            Import tab (old messages stay, missing files are added).
          </p>
        {:else if isImage(a) && srcs[keyOf(a)]}
          <img
            src={srcs[keyOf(a)]}
            alt={a.filename || "image"}
            class="max-h-64 max-w-full rounded-md border border-border"
            onerror={() => {
              broken = { ...broken, [keyOf(a)]: true };
            }}
          />
        {:else if isAudio(a) && srcs[keyOf(a)]}
          <audio
            class="w-full"
            controls
            src={srcs[keyOf(a)]}
            onerror={() => {
              broken = { ...broken, [keyOf(a)]: true };
            }}
          ></audio>
        {:else if !broken[keyOf(a)] && !srcs[keyOf(a)]}
          <p class="text-xs text-muted-foreground">Loading {a.filename || "attachment"}…</p>
        {:else}
          <p class="text-xs text-muted-foreground">
            Stored locally: {a.filename || a.kind}
            {#if a.mime}
              ({a.mime})
            {/if}
          </p>
        {/if}
      </li>
    {/each}
  </ul>
{/if}
