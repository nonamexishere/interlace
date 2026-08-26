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
    onGoPeople,
    onToast,
    friendly,
  }: {
    issues?: string[];
    onError: (e: unknown) => void;
    onDone: () => Promise<void>;
    onGoPeople: () => void;
    onToast?: (message: string) => void;
    friendly: (raw: string) => string;
  } = $props();

  let busy = $state(false);
  let scanning = $state(true);
  let scanError = $state("");
  let scanGen = 0;
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
    const gen = ++scanGen;
    scanning = true;
    scanError = "";
    try {
      const next = await api.doctorIssues();
      if (gen !== scanGen) return;
      issues = next;
    } catch (e) {
      if (gen === scanGen) {
        scanError = friendly(e instanceof Error ? e.message : String(e ?? ""));
      }
    } finally {
      if (gen === scanGen) scanning = false;
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
      scanError = "";
      await onDone();
    } catch (e) {
      onError(e);
    } finally {
      busy = false;
      pending = null;
    }
  }

  async function revealArchive() {
    try {
      await api.revealArchive();
    } catch {
      onToast?.("Could not reveal");
    }
  }

  onMount(() => {
    load();
  });
</script>

<ScrollArea class="p-4">
  <h1 class="mb-1 text-xl font-semibold tracking-tight">{t("doctor")}</h1>
  <p class="mb-4 text-sm text-muted-foreground">
    {t("doctorPaneLead")}
  </p>

  {#if scanning}
    <p class="text-sm text-muted-foreground">Scanning SQLite, FTS, and referenced CAS blobs…</p>
  {:else if scanError}
    <div
      class="rounded-md border border-destructive/40 bg-muted/40 px-4 py-6 text-sm"
      data-partial
    >
      <p class="font-medium text-destructive">Error</p>
      <p class="mt-1 text-muted-foreground">{scanError}</p>
      <Button size="sm" class="mt-3" onclick={load}>Retry</Button>
    </div>
  {:else if issues.length === 0}
    <EmptyState
      title={t("noDoctorIssues")}
      body={t("doctorEmptyBody")}
      actionLabel={t("people")}
      onAction={onGoPeople}
    />
  {:else}
    <div
      class="rounded-md border border-warning bg-warning/15 p-3 text-sm text-warning"
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
      disabled={busy || scanning}
      onclick={() =>
        ask(
          t("runIntegrityCheck"),
          t("runIntegrityCheckDesc"),
          t("integrityCheck"),
          { integrity: true, rebuildFts: false, gcCas: false },
          t("integrityCheckFinished"),
        )}
    >
      Integrity
    </Button>
    <Button
      variant="outline"
      size="sm"
      disabled={busy || scanning}
      onclick={() =>
        ask(
          t("rebuildSearchIndex"),
          t("rebuildSearchIndexDesc"),
          t("rebuild"),
          { integrity: false, rebuildFts: true, gcCas: false },
          t("ftsRebuildFinished"),
        )}
    >
      Rebuild FTS
    </Button>
    <Button
      variant="outline"
      size="sm"
      disabled={busy || scanning}
      onclick={() =>
        ask(
          t("gcUnusedCas"),
          t("gcUnusedCasDesc"),
          t("deleteUnused"),
          { integrity: false, rebuildFts: false, gcCas: true },
          t("casGcFinished"),
        )}
    >
      GC CAS
    </Button>
    <Button variant="ghost" size="sm" disabled={busy || scanning} onclick={load}>Refresh</Button>
  </div>

  <section class="mt-8 max-w-xl space-y-2 text-sm">
    <h2 class="font-medium">Backup</h2>
    <p>
      {t("backupUnit")} Copy <code class="text-xs">INTERLACE.toml</code>,
      <code class="text-xs">archive.sqlite*</code>, <code class="text-xs">cas/</code>, and
      <code class="text-xs">logs/</code>. {t("noSeparateBackup")}
    </p>
    <p>
      {t("notEncryptedAtRest")} This app does not use SQLCipher and
      does not claim encryption.
    </p>
    <p>
      {t("doNotKeepLive")} {t("timeMachineOk")}
      <code class="text-xs">docs/user/backup.md</code>.
    </p>
    <Button variant="outline" size="sm" data-reveal-archive onclick={revealArchive}>
      {t("revealInFinder")}
    </Button>
  </section>
</ScrollArea>

<ConfirmDialog
  bind:open={confirmOpen}
  title={confirmTitle}
  description={confirmDesc}
  confirmLabel={confirmLabel}
  onconfirm={runPending}
  onerror={onError}
/>
