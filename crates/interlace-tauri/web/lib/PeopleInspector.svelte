<script lang="ts">
  import { fly } from "svelte/transition";
  import type { Identity, Person } from "./api";
  import { humanTime } from "./formatTime";
  import { Button } from "$lib/components/ui/button/index.js";
  import { t } from "$lib/i18n";
  import { chromeMotionMs } from "$lib/motion";
  import { writeIncludeGroupsPref } from "./PeoplePrefs";

  let {
    showPersonChrome = $bindable(false),
    personTitle,
    selectedPerson,
    identities,
    selectedId,
    includeGroups = $bindable(false),
    personById,
    onMerge,
    onUnlink,
    onReloadPerson,
  }: {
    showPersonChrome?: boolean;
    personTitle: string;
    selectedPerson: Person | undefined;
    identities: Identity[];
    selectedId: number | null;
    includeGroups?: boolean;
    personById: (id: number | null) => Person | undefined;
    onMerge: () => void;
    onUnlink: (id: number) => void;
    onReloadPerson: (includeGroups: boolean) => void;
  } = $props();
</script>

{#if showPersonChrome}
<aside
  data-person-inspector
  tabindex="-1"
  class="flex w-72 shrink-0 flex-col gap-3 overflow-y-auto border-l border-border p-4 text-sm"
  aria-label={t("inspector")}
  transition:fly={{ x: 16, duration: chromeMotionMs() }}
>
  <button
    type="button"
    class="text-left font-medium focus-visible:ring-2 focus-visible:ring-ring"
    onclick={() => (showPersonChrome = !showPersonChrome)}
  >{personTitle}</button>
  <p class="text-xs text-muted-foreground">
    {t("lastActivity")}
    {humanTime(selectedPerson?.last_activity_at)}
  </p>
  <div class="flex flex-col gap-2">
    <Button variant="outline" size="sm" disabled={!personById(selectedId)} onclick={onMerge}
      >Merge…</Button
    >
    <label class="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        class="focus-visible:ring-2 focus-visible:ring-ring"
        bind:checked={includeGroups}
        onchange={() => { writeIncludeGroupsPref(includeGroups); onReloadPerson(includeGroups); }}
      />
      include groups
    </label>
  </div>
  <p class="text-xs font-medium">{t("identities")}</p>
  <ul class="space-y-1 text-sm text-muted-foreground">
    {#each identities as ident}
      <li class="flex items-center justify-between gap-2">
        <span>{ident.kind} {ident.value || ident.display_name || ""}</span>
        <Button variant="outline" size="sm" onclick={() => onUnlink(ident.id)}>unlink</Button>
      </li>
    {/each}
  </ul>
</aside>
{/if}
