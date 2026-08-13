<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "./api";
  import { Button } from "$lib/components/ui/button/index.js";
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import ConfirmDialog from "$lib/ConfirmDialog.svelte";
  import EmptyState from "$lib/EmptyState.svelte";
  import { t } from "$lib/i18n";

  let {
    issues = $bindable<string[]>([]),
    onError,
    onDone,
  }: {
    issues?: string[];
    onError: (e: unknown) => void;
    onDone: () => Promise<void>;
  } = $props();

  let busy = $state(false);
  let lastOk = $state("");
  let confirmOpen = $state(false);
  let confirmTitle = $state("");
  let confirmDesc = $state("");
  let confirmLabel = $state("Run");
  let pending: {
    integrity: boolean;
    rebuildFts: boolean;
    gcCas: boolean;
    ok: string;
  } | null = null;

  async function load() {
    try {
      issues = await api.doctorIssues();
    } catch (e) {
      onError(e);
    }
  }

  function ask(
    title: string,
    description: string,
    label: string,
    flags: { integrity: boolean; rebuildFts: boolean; gcCas: boolean },
    ok: string,
  ) {
    confirmTitle = title;
    confirmDesc = description;
    confirmLabel = label;
    pending = { ...flags, ok };
    confirmOpen = true;
  }

  async function runPending() {
    if (!pending) return;
    busy = true;
    lastOk = "";
    try {
      issues = await api.doctorRun({
        integrity: pending.integrity,
        rebuildFts: pending.rebuildFts,
        gcCas: pending.gcCas,
      });
      lastOk = pending.ok;
      await onDone();
    } catch (e) {
      onError(e);
    } finally {
      busy = false;
      pending = null;
    }
  }

  onMount(() => {
    load();
  });
</script>

<ScrollArea class="p-4">
  <h1 class="mb-1 text-xl font-semibold tracking-tight">{t("doctor")}</h1>
  <p class="mb-4 text-sm text-muted-foreground">
    Same checks as <code class="text-xs">interlace doctor</code>. This window already holds the
    archive lock — close it before running doctor in a terminal.
  </p>

  {#if issues.length === 0}
    <EmptyState
      title="No doctor issues"
      body="SQLite, FTS, and referenced CAS blobs look healthy. Unreferenced files still need GC CAS if you want them gone."
    />
  {:else}
    <div
      class="rounded-md border border-amber-700/40 bg-amber-950/20 p-3 text-sm text-amber-800 dark:text-amber-300"
    >
      <p class="font-medium">Doctor found issues</p>
      <ul class="mt-1 list-disc pl-4">
        {#each issues as d}
          <li>{d}</li>
        {/each}
      </ul>
    </div>
  {/if}

  {#if lastOk}
    <p class="mt-3 text-sm text-muted-foreground">{lastOk}</p>
  {/if}

  <div class="mt-4 flex flex-wrap gap-2">
    <Button
      variant="outline"
      size="sm"
      disabled={busy}
      onclick={() =>
        ask(
          "Run integrity check?",
          "Read-only PRAGMA integrity_check plus FTS integrity. Does not change messages.",
          "Check",
          { integrity: true, rebuildFts: false, gcCas: false },
          "Integrity check finished.",
        )}
    >
      Integrity
    </Button>
    <Button
      variant="outline"
      size="sm"
      disabled={busy}
      onclick={() =>
        ask(
          "Rebuild search index?",
          "Recreates FTS triggers if missing and rebuilds the index. Messages and CAS stay put.",
          "Rebuild",
          { integrity: false, rebuildFts: true, gcCas: false },
          "FTS rebuild finished.",
        )}
    >
      Rebuild FTS
    </Button>
    <Button
      variant="outline"
      size="sm"
      disabled={busy}
      onclick={() =>
        ask(
          "Garbage-collect unused CAS files?",
          "Deletes blobs not referenced by attachments or contact photos. Cannot undo. Close other writers first.",
          "Delete unused",
          { integrity: false, rebuildFts: false, gcCas: true },
          "CAS GC finished.",
        )}
    >
      GC CAS
    </Button>
    <Button variant="ghost" size="sm" disabled={busy} onclick={load}>Refresh</Button>
  </div>

  <section class="mt-8 max-w-xl space-y-2 text-sm">
    <h2 class="font-medium">Backup</h2>
    <p>
      The folder is the backup unit. Copy <code class="text-xs">INTERLACE.toml</code>,
      <code class="text-xs">archive.sqlite*</code>, <code class="text-xs">cas/</code>, and
      <code class="text-xs">logs/</code>. There is no separate backup command.
    </p>
    <p>
      Not encrypted at rest. FileVault is your encryption. This app does not use SQLCipher and
      does not claim encryption.
    </p>
    <p>
      Do not keep the <em>live</em> archive in iCloud Drive, Dropbox, or Google Drive. Time Machine
      of the whole folder is fine after you close this window. See
      <code class="text-xs">docs/user/backup.md</code>.
    </p>
  </section>
</ScrollArea>

<ConfirmDialog
  bind:open={confirmOpen}
  title={confirmTitle}
  description={confirmDesc}
  confirmLabel={confirmLabel}
  onconfirm={runPending}
/>
