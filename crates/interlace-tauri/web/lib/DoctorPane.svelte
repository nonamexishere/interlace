<script lang="ts">
  import { onMount } from "svelte";
  import { api, type DoctorPlan } from "./api";
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
  let lastImport = $state<{ inserted_messages?: number } | null>(null);
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
  let voiceOn = $state(false);
  let voiceAsk = $state(false);
  let ocrOn = $state(false);
  let ocrAsk = $state(false);
  let snapshots = $state<string[]>([]);
  let snapshotAsk = $state<string | null>(null);
  let repairPlan = $state<DoctorPlan | null>(null);
  let repairAsk = $state(false);

  async function load() {
    const gen = ++scanGen;
    scanning = true;
    scanError = "";
    try {
      const next = await api.doctorIssues();
      if (gen !== scanGen) return;
      issues = next;
      try {
        const st = await api.status();
        if (gen !== scanGen) return;
        lastImport = st.last_import ?? null;
      } catch {
        if (gen === scanGen) lastImport = null;
      }
    } catch (e) {
      if (gen === scanGen) {
        scanError = friendly(e instanceof Error ? e.message : String(e ?? ""));
      }
    } finally {
      try {
        const listed = await api.snapshotList();
        if (gen === scanGen) snapshots = listed;
      } catch {
        if (gen === scanGen) snapshots = [];
      }
      if (gen === scanGen) scanning = false;
    }
  }

  function formatSi(n: number): string {
    const units = ["B", "KB", "MB", "GB"];
    if (n === 0) return "0 B";
    let v = n;
    let i = 0;
    while (v >= 1000 && i < units.length - 1) {
      v /= 1000;
      i += 1;
    }
    return (v % 1 === 0 ? String(v) : v.toFixed(1)) + " " + units[i];
  }

  async function estimateThenAsk() {
    busy = true;
    let desc = t("gcUnusedCasDesc");
    try {
      const n = await api.estimateUnreferencedCasBytes();
      desc = t("gcUnusedCasBytes").replace("{n}", formatSi(n));
    } catch {
      // keep today's unsized copy; GC still runnable
    } finally {
      busy = false;
    }
    ask(
      t("gcUnusedCas"),
      desc,
      t("deleteUnused"),
      { integrity: false, rebuildFts: false, gcCas: true },
      t("casGcFinished"),
    );
  }

  function repairPlanEmpty() {
    const plan = repairPlan;
    if (!plan) return true;
    return !plan.rebuild_search && plan.reattach.length === 0 && plan.reclaim.length === 0;
  }

  async function planRepair() {
    busy = true;
    try {
      repairPlan = await api.doctorPlan();
    } catch (e) {
      onError(e);
    } finally {
      busy = false;
    }
  }

  function askRepair() {
    repairAsk = true;
    voiceAsk = false;
    ocrAsk = false;
    snapshotAsk = null;
    pending = null;
    confirmTitle = t("doctorRepairTitle");
    confirmDesc = t("doctorRepairBody");
    confirmLabel = t("doctorRepairApply");
    confirmOpen = true;
  }

  async function runRepair() {
    const plan = repairPlan;
    if (!plan) {
      repairAsk = false;
      return;
    }
    busy = true;
    try {
      await api.doctorApply(plan);
      lastOk = t("doctorRepairDone");
      repairPlan = await api.doctorPlan();
    } catch (e) {
      onError(e);
    } finally {
      busy = false;
      repairAsk = false;
    }
  }

  function ask(
    title: string,
    description: string,
    label: string,
    flags: { integrity: boolean; rebuildFts: boolean; gcCas: boolean },
    ok: string,
  ) {
    repairAsk = false;
    voiceAsk = false;
    ocrAsk = false;
    snapshotAsk = null;
    confirmTitle = title;
    confirmDesc = description;
    confirmLabel = label;
    pending = { ...flags, ok };
    confirmOpen = true;
  }

  async function readEnabled() {
    try {
      voiceOn = await api.voiceTranscribeEnabled();
    } catch {
      voiceOn = false;
    }
  }

  async function readOcrEnabled() {
    try {
      ocrOn = await api.ocrImagesEnabled();
    } catch {
      ocrOn = false;
    }
  }

  $effect(() => {
    void readEnabled();
  });

  $effect(() => {
    void readOcrEnabled();
  });

  async function onVoiceToggle(on: boolean) {
    voiceOn = on;
    try {
      await api.setVoiceTranscribeEnabled(on);
    } catch (e) {
      onError(e);
      void readEnabled();
    }
  }

  async function onOcrToggle(on: boolean) {
    ocrOn = on;
    try {
      await api.setOcrImagesEnabled(on);
    } catch (e) {
      onError(e);
      void readOcrEnabled();
    }
  }

  function askVoice() {
    voiceAsk = true;
    ocrAsk = false;
    snapshotAsk = null;
    repairAsk = false;
    pending = null;
    confirmTitle = t("transcribeVoice");
    confirmDesc = t("transcribeVoiceDesc");
    confirmLabel = t("transcribeVoice");
    confirmOpen = true;
  }

  async function runVoice() {
    busy = true;
    lastOk = "";
    try {
      await api.transcribeVoiceNotes();
      lastOk = t("transcribeVoiceFinished");
    } catch (e) {
      onError(e);
    } finally {
      busy = false;
      voiceAsk = false;
    }
  }

  function askOcr() {
    ocrAsk = true;
    voiceAsk = false;
    snapshotAsk = null;
    repairAsk = false;
    pending = null;
    confirmTitle = t("ocrImages");
    confirmDesc = t("ocrImagesDesc");
    confirmLabel = t("ocrImages");
    confirmOpen = true;
  }

  async function runOcr() {
    busy = true;
    lastOk = "";
    try {
      await api.ocrImages();
      lastOk = t("ocrImagesFinished");
    } catch (e) {
      onError(e);
    } finally {
      busy = false;
      ocrAsk = false;
    }
  }

  function askSnapshot(id: string) {
    snapshotAsk = id;
    voiceAsk = false;
    ocrAsk = false;
    repairAsk = false;
    pending = null;
    confirmTitle = t("snapshotRestoreTitle");
    confirmDesc = t("snapshotRestoreBody");
    confirmLabel = t("snapshotRestore");
    confirmOpen = true;
  }

  async function takeSnapshot() {
    busy = true;
    try {
      await api.snapshotTake();
      onToast?.(t("snapshotSaved"));
      try {
        snapshots = await api.snapshotList();
      } catch {
        snapshots = [];
      }
    } catch (e) {
      const raw = e instanceof Error ? e.message : String(e ?? "");
      if (raw.includes("import running")) onToast?.(t("importRunning"));
      else onError(e);
    } finally {
      busy = false;
    }
  }

  async function runSnapshot() {
    const id = snapshotAsk;
    if (!id) return;
    busy = true;
    try {
      await api.snapshotRestore(id);
    } catch (e) {
      const raw = e instanceof Error ? e.message : String(e ?? "");
      onToast?.(
        raw.includes("import running") ? t("importRunning") : t("snapshotRestoreFailed"),
      );
      return;
    } finally {
      busy = false;
      snapshotAsk = null;
    }
    onToast?.(t("snapshotRestored"));
    try {
      await load();
      await onDone();
    } catch (e) {
      onError(e);
    }
  }

  async function runPending() {
    if (repairAsk) {
      await runRepair();
      return;
    }
    if (ocrAsk) {
      await runOcr();
      return;
    }
    if (voiceAsk) {
      await runVoice();
      return;
    }
    if (snapshotAsk) {
      await runSnapshot();
      return;
    }
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

  async function copyArchiveTo() {
    try {
      const copied = await api.copyArchiveTo();
      if (copied) onToast?.(t("archiveCopied"));
    } catch (e) {
      const raw = e instanceof Error ? e.message : String(e ?? "");
      onToast?.(raw.includes("import running") ? t("importRunning") : "Could not copy archive");
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
  <p class="mb-4 text-sm text-muted-foreground">
    {t("doctorLastInserted").replace(
      "{n}",
      String(lastImport?.inserted_messages ?? 0),
    )}
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

  {#if repairPlan}
    <ul data-doctor-repair-list class="mt-3 list-disc pl-4 text-sm text-muted-foreground">
      {#if repairPlan.rebuild_search}
        <li>{t("doctorRepairRebuild")}</li>
      {/if}
      {#each repairPlan.reattach as hash (hash)}
        <li>{t("doctorRepairReattach").replace("{hash}", hash)}</li>
      {/each}
      {#each repairPlan.reclaim as hash (hash)}
        <li>{t("doctorRepairReclaim").replace("{hash}", hash)}</li>
      {/each}
    </ul>
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
      onclick={estimateThenAsk}
    >
      GC CAS
    </Button>
    <Button
      variant="outline"
      size="sm"
      data-doctor-repair
      disabled={busy || scanning}
      onclick={planRepair}
    >
      {t("doctorRepair")}
    </Button>
    <Button
      variant="outline"
      size="sm"
      data-doctor-repair-apply
      disabled={busy || scanning || repairPlanEmpty()}
      onclick={askRepair}
    >
      {t("doctorRepairApply")}
    </Button>
    <Button variant="ghost" size="sm" disabled={busy || scanning} onclick={load}>Refresh</Button>
    <label class="inline-flex items-center gap-2 px-1 text-sm">
      <input
        type="checkbox"
        class="focus-visible:ring-2 focus-visible:ring-ring"
        data-vt-enabled
        checked={voiceOn}
        disabled={busy || scanning}
        onchange={(event) => onVoiceToggle(event.currentTarget.checked)}
      />
      {t("transcribeVoiceLabel")}
    </label>
    <Button
      variant="outline"
      size="sm"
      data-vt-run
      disabled={busy || scanning}
      onclick={askVoice}
    >
      {t("transcribeVoice")}
    </Button>
    <label class="inline-flex items-center gap-2 px-1 text-sm">
      <input
        type="checkbox"
        class="focus-visible:ring-2 focus-visible:ring-ring"
        data-ocr-enabled
        checked={ocrOn}
        disabled={busy || scanning}
        onchange={(event) => onOcrToggle(event.currentTarget.checked)}
      />
      {t("ocrImagesLabel")}
    </label>
    <Button
      variant="outline"
      size="sm"
      data-ocr-run
      disabled={busy || scanning}
      onclick={askOcr}
    >
      {t("ocrImages")}
    </Button>
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
    <Button
      variant="outline"
      size="sm"
      data-copy-archive
      disabled={busy || scanning}
      onclick={copyArchiveTo}
    >
      {t("copyArchiveTo")}
    </Button>
    <div data-snapshot-list class="space-y-2 pt-2">
      <p class="font-medium">{t("snapshots")}</p>
      {#if snapshots.length > 0}
        <ul class="space-y-1">
          {#each snapshots as id (id)}
            <li class="flex flex-wrap items-center justify-between gap-2">
              <span class="font-mono text-xs">{id}</span>
              <Button
                variant="outline"
                size="sm"
                data-snapshot-restore
                disabled={busy || scanning}
                onclick={() => askSnapshot(id)}
              >
                {t("snapshotRestore")}
              </Button>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
    <Button
      variant="outline"
      size="sm"
      data-snapshot-take
      disabled={busy || scanning}
      onclick={takeSnapshot}
    >
      {t("snapshotTake")}
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
