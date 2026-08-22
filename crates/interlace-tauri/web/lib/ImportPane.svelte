<script lang="ts">
  import { api, type ImportProgress } from "./api";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Label } from "$lib/components/ui/label/index.js";
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import EmptyState from "./EmptyState.svelte";

  let {
    onError,
    onToast,
    onDone,
  }: {
    onError: (e: unknown) => void;
    onToast?: (message: string) => void;
    onDone: () => Promise<void>;
  } = $props();

  let kind = $state("auto");
  let locale = $state("");
  let path = $state("");
  let progress = $state<ImportProgress>({ status: "idle" });
  let timer: ReturnType<typeof setInterval> | null = null;

  async function pick(folder: boolean) {
    try {
      const p = await api.pickImportPath(folder);
      if (p) path = p;
    } catch (e) {
      onError(e);
    }
  }

  async function start() {
    if (!path) {
      onToast?.("pick a file or folder first");
      return;
    }
    try {
      await api.importStart({
        path,
        kind: kind === "auto" ? null : kind,
        locale: locale.trim() || null,
      });
      poll();
    } catch (e) {
      onError(e);
    }
  }

  async function tick() {
    try {
      progress = await api.importProgress();
      if (progress.status === "done" || progress.status === "failed") {
        if (timer) {
          clearInterval(timer);
          timer = null;
        }
        if (progress.status === "failed" && progress.error) {
          onError(new Error(progress.error));
        }
        if (progress.status === "done") {
          await onDone();
        }
      }
    } catch (e) {
      onError(e);
    }
  }

  function poll() {
    if (timer) clearInterval(timer);
    timer = setInterval(tick, 400);
    tick();
  }

  $effect(() => {
    poll();
    return () => {
      if (timer) clearInterval(timer);
    };
  });
</script>

<ScrollArea class="p-4">
  <h1 class="mb-3 text-xl font-semibold tracking-tight">Import</h1>
  <p class="mb-4 text-sm text-muted-foreground">
    Folder/file picker only — no URLs. WhatsApp: pick one .zip <em>or</em> a folder of zips.
    Takeout: pick the Takeout directory. Bodies are not dumped here.
  </p>
  {#if !path && progress.status !== "running"}
    <div class="mb-4 max-w-lg">
      <EmptyState
        title="No file selected"
        body="Pick a WhatsApp ZIP, Takeout folder, mbox, or contacts file. Folder picker only — no URLs."
        actionLabel="Pick file"
        onAction={() => pick(false)}
      />
    </div>
  {/if}
  <div class="max-w-lg space-y-3">
    <div class="space-y-1.5">
      <Label for="kind">Kind</Label>
      <select
        id="kind"
        bind:value={kind}
        class="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring"
      >
        <option value="auto">auto-detect</option>
        <option value="whatsapp">whatsapp zip</option>
        <option value="takeout">takeout zip/dir</option>
        <option value="gmail">gmail mbox</option>
        <option value="contacts">contacts vcf/csv</option>
      </select>
    </div>
    <div class="space-y-1.5">
      <Label for="loc">Locale (WhatsApp, optional)</Label>
      <Input id="loc" bind:value={locale} placeholder="tr-TR · leave empty to probe" />
    </div>
    <p class="break-all text-xs text-muted-foreground">{path || "no file selected"}</p>
    <div class="flex flex-wrap gap-2">
      <Button variant="outline" onclick={() => pick(false)}>Pick file…</Button>
      <Button variant="outline" onclick={() => pick(true)}>Pick folder…</Button>
      <Button onclick={start} disabled={progress.status === "running"}>Start import</Button>
    </div>
    <p class="text-sm">
      Status: <strong>{progress.status}</strong>
      {#if progress.kind}
        · {progress.kind}
      {/if}
      {#if progress.detail}
        · {progress.detail}
      {/if}
    </p>
    {#if progress.stats}
      <dl class="grid grid-cols-[10rem_1fr] gap-1 text-sm">
        <dt class="text-muted-foreground">messages</dt>
        <dd>{progress.stats.inserted_messages} inserted, {progress.stats.skipped_dupes} dupes</dd>
        <dt class="text-muted-foreground">identities</dt>
        <dd>{progress.stats.inserted_identities}</dd>
        <dt class="text-muted-foreground">attachments</dt>
        <dd>{progress.stats.attachments_stored}</dd>
        <dt class="text-muted-foreground">warnings / rejected</dt>
        <dd>{progress.stats.warnings} / {progress.stats.rejected}</dd>
        <dt class="text-muted-foreground">review</dt>
        <dd>{progress.stats.review_enqueued} enqueued</dd>
      </dl>
    {/if}
    {#if progress.error}
      <p class="text-sm text-destructive">{progress.error}</p>
    {/if}
  </div>
</ScrollArea>
