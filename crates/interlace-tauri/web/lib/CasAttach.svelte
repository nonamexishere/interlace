<script lang="ts">
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

  function casUrl(hash: string) {
    return `cas://localhost/${hash}`;
  }

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

  let broken = $state<Record<number, boolean>>({});
</script>

{#if items?.length}
  <ul class="mt-2 space-y-2">
    {#each items as a}
      <li>
        {#if a.omitted}
          <p class="text-xs text-muted-foreground">Media omitted in this export</p>
        {:else if a.missing}
          <p class="text-xs text-muted-foreground">Referenced media was not in the ZIP</p>
        {:else if a.cas_hash && isImage(a) && !broken[a.id]}
          <img
            src={casUrl(a.cas_hash)}
            alt={a.filename || "image"}
            class="max-h-64 max-w-full rounded-md border border-border"
            onerror={() => {
              broken = { ...broken, [a.id]: true };
            }}
          />
        {:else if a.cas_hash && isAudio(a) && !broken[a.id]}
          <audio
            class="w-full"
            controls
            src={casUrl(a.cas_hash)}
            onerror={() => {
              broken = { ...broken, [a.id]: true };
            }}
          ></audio>
        {:else if a.cas_hash}
          <p class="text-xs text-muted-foreground">
            Stored locally: {a.filename || a.kind}
            {#if a.mime}
              ({a.mime})
            {/if}
          </p>
        {:else}
          <p class="text-xs text-muted-foreground">Attachment recorded, no bytes in CAS</p>
        {/if}
      </li>
    {/each}
  </ul>
{/if}
