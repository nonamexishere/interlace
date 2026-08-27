<script lang="ts">
  import { api, type Status } from "./api";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Label } from "$lib/components/ui/label/index.js";
  import { t } from "$lib/i18n";

  let {
    region = $bindable(""),
    name = $bindable(""),
    emails = $bindable(""),
    phones = $bindable(""),
    onError,
    applyStatus,
    onOpenExisting,
    onBegin,
  }: {
    region?: string;
    name?: string;
    emails?: string;
    phones?: string;
    onError: (e: unknown) => void;
    applyStatus: (next: Status) => Promise<void>;
    onOpenExisting: () => Promise<void>;
    onBegin: () => void;
  } = $props();

  function csv(s: string) {
    return s.split(",").map((x) => x.trim()).filter(Boolean);
  }

  async function createArchive() {
    onBegin();
    const r = region.trim();
    if (!r) {
      onError("phone-region is required (e.g. TR, US)");
      return;
    }
    try {
      const folder = await api.pickFolder();
      if (!folder) return;
      await applyStatus(
        await api.init({
          path: folder,
          phoneRegion: r,
          name: name.trim() || null,
          emails: csv(emails),
          phones: csv(phones),
        }),
      );
    } catch (e) {
      onError(e);
    }
  }

  async function openPicker() {
    await onOpenExisting();
  }
</script>

<main class="mx-auto w-full max-w-lg space-y-4 p-6">
  <h1 class="text-2xl font-semibold tracking-tight">{t("openAnArchive")}</h1>
  <p class="text-muted-foreground">
    Offline archive. No account. No sync. This window never phones home.
  </p>
  <div class="space-y-1.5">
    <Label for="region">Required phone-region (ISO 3166-1 alpha-2)</Label>
    <Input id="region" bind:value={region} maxlength={2} placeholder="TR" />
  </div>
  <details class="rounded-md border border-border bg-muted/40 px-3 py-2">
    <summary
      class="cursor-pointer text-xs font-medium text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
    >
      More
    </summary>
    <div class="mt-3 space-y-3">
      <div class="space-y-1.5">
        <Label for="name">Your name</Label>
        <Input id="name" bind:value={name} placeholder="optional" />
      </div>
      <div class="space-y-1.5">
        <Label for="emails">Emails (comma-separated)</Label>
        <Input id="emails" bind:value={emails} placeholder="optional" />
      </div>
      <div class="space-y-1.5">
        <Label for="phones">Phones (comma-separated)</Label>
        <Input id="phones" bind:value={phones} placeholder="optional" />
      </div>
    </div>
  </details>
  <div class="flex gap-2">
    <Button onclick={createArchive}>{t("createArchive")}</Button>
    <Button variant="outline" onclick={openPicker}>{t("openExisting")}</Button>
  </div>
  <p class="text-sm text-muted-foreground">
    Folder picker only — no URLs. Phone-region has no silent default. The folder is the backup
    unit. Not encrypted at rest; use FileVault.
  </p>
</main>
