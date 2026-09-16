<script lang="ts">
  import type { LinkEvent, Person, Status } from "./api";
  import { writePeopleSortPref } from "./PeoplePrefs";
  import { humanTime } from "./formatTime";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Label } from "$lib/components/ui/label/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import EmptyState from "$lib/EmptyState.svelte";
  import PersonAvatar from "./PersonAvatar.svelte";
  import { t } from "$lib/i18n";
  import PanelLeft from "@lucide/svelte/icons/panel-left";
  import PanelLeftClose from "@lucide/svelte/icons/panel-left-close";
  import Pin from "@lucide/svelte/icons/pin";
  import PinOff from "@lucide/svelte/icons/pin-off";

  let {
    st,
    people,
    filtered,
    filter = $bindable(""),
    peopleSort = $bindable("recent"),
    selectedId,
    peopleTabId,
    peopleLoading,
    sidebarCollapsed,
    undoableEvents,
    onSelectPerson,
    onUndo,
    onReveal,
    onOpenPicker,
    onImport,
    persistSidebar,
    undoRowLabel,
    pinIds,
    onTogglePin,
  }: {
    st: Status;
    people: Person[];
    filtered: Person[];
    filter?: string;
    peopleSort?: string;
    selectedId: number | null;
    peopleTabId: number | null;
    peopleLoading: boolean;
    sidebarCollapsed: boolean;
    undoableEvents: LinkEvent[];
    onSelectPerson: (id: number) => void;
    onUndo: (id: number) => void;
    onReveal: () => void;
    onOpenPicker: () => void;
    onImport: () => void;
    persistSidebar: (next: boolean) => void;
    undoRowLabel: (e: LinkEvent) => string;
    pinIds: number[];
    onTogglePin: (id: number) => void;
  } = $props();

  const pinSet = $derived(new Set(pinIds));
  const pinnedMatching = $derived(filtered.filter((p) => pinSet.has(p.id)));

  function setSort(next: "recent" | "az") {
    peopleSort = next;
    writePeopleSortPref(next);
  }
</script>

<div
  data-people-sidebar
  data-people-sidebar-collapsed={sidebarCollapsed ? true : undefined}
  aria-busy={peopleLoading}
  class="min-h-0 min-w-0 shrink-0 overflow-x-hidden overflow-y-auto border-r border-border {sidebarCollapsed
    ? 'w-12 p-1'
    : 'w-72 p-4'}"
>
  <div class="flex {sidebarCollapsed ? 'justify-center' : 'justify-end'}">
    <Button
      variant="ghost"
      size="icon"
      class="size-8 shrink-0"
      data-sidebar-toggle
      aria-expanded={!sidebarCollapsed}
      aria-label={sidebarCollapsed ? t("expandSidebar") : t("collapseSidebar")}
      onclick={() => persistSidebar(!sidebarCollapsed)}
    >
      {#if !sidebarCollapsed}
        <PanelLeftClose class="size-4" />
      {:else}
        <PanelLeft class="size-4" />
      {/if}
    </Button>
  </div>
  {#if !sidebarCollapsed}
    <p class="break-all text-xs text-muted-foreground">{st.path}</p>
    <Button
      variant="ghost"
      size="sm"
      class="mt-1 h-7 px-2 text-xs"
      data-reveal-archive
      onclick={onReveal}
    >
      {t("revealInFinder")}
    </Button>
    <dl class="mt-3 grid min-w-0 grid-cols-[auto_minmax(0,1fr)] gap-x-2 gap-y-1 text-sm">
      <dt class="text-muted-foreground">owner</dt>
      <dd class="min-w-0 truncate">{st.owner_display_name || "—"}</dd>
      <dt class="text-muted-foreground">region</dt>
      <dd class="min-w-0 truncate">{st.default_phone_region || "—"}</dd>
      <dt class="text-muted-foreground">messages</dt>
      <dd class="min-w-0 truncate">{st.messages}</dd>
      <dt class="text-muted-foreground">identities</dt>
      <dd class="min-w-0 truncate">{st.identities}</dd>
      <dt class="text-muted-foreground">persons</dt>
      <dd class="min-w-0 truncate">{st.persons_live}</dd>
      <dt class="text-muted-foreground">review</dt>
      <dd class="min-w-0 truncate">{st.review_open}</dd>
    </dl>
    <p class="mt-2 truncate text-xs text-muted-foreground">
      {st.last_import
        ? `last import id=${st.last_import.id} status=${st.last_import.status}`
        : "no imports yet"}
    </p>
    {#if st.warnings?.length}
      <ul class="mt-2 min-w-0 list-disc pl-4 text-sm text-muted-foreground">
        {#each st.warnings as w}
          <li class="break-words">{w}</li>
        {/each}
      </ul>
    {/if}
  {/if}
  <div class={sidebarCollapsed ? "sr-only" : "mt-4 min-w-0 space-y-1.5"}>
    <Label for="person-filter">Filter people</Label>
    <div class="flex min-w-0 items-center gap-1">
      <Input id="person-filter" type="search" bind:value={filter} placeholder="name" class="min-w-0" />
      <Button variant={peopleSort === "recent" ? "secondary" : "ghost"} size="sm" class="h-7 px-2 text-xs" aria-pressed={peopleSort === "recent"} onclick={() => setSort("recent")}>Recent</Button>
      <Button variant={peopleSort === "az" ? "secondary" : "ghost"} size="sm" class="h-7 px-2 text-xs" aria-pressed={peopleSort === "az"} onclick={() => setSort("az")}>A–Z</Button>
    </div>
  </div>
  {#if !sidebarCollapsed && pinnedMatching.length > 0}
    <p class="mt-2 text-xs text-muted-foreground">{t("pinned")}</p>
  {/if}
  <ul class="mt-2 min-w-0 space-y-0.5" role="listbox" aria-label="People" aria-busy={peopleLoading}>
    {#each filtered as p (p.id)}
      <li class="min-w-0" role="presentation">
        {#if sidebarCollapsed}
          <button
            type="button"
            role="option"
            aria-selected={selectedId === p.id}
            tabindex={p.id === peopleTabId ? 0 : -1}
            title={p.display_name}
            aria-label={`${p.display_name}${p.is_self ? " (self)" : ""}${p.last_activity_at ? ` ${humanTime(p.last_activity_at)}` : ""}`}
            class="flex w-full min-w-0 max-w-full justify-center rounded-md px-0 py-1 text-sm hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring {selectedId === p.id
              ? 'bg-accent'
              : ''} {p.is_self ? 'font-semibold' : ''}"
            onclick={() => onSelectPerson(p.id)}
          >
            <PersonAvatar
              personId={p.id}
              display_name={p.display_name}
              photo_cas_hash={p.photo_cas_hash}
            />
          </button>
        {:else}
          <div class="flex min-w-0 items-start gap-0.5">
            <button
              type="button"
              role="option"
              aria-selected={selectedId === p.id}
              tabindex={p.id === peopleTabId ? 0 : -1}
              title={p.display_name}
              aria-label={`${p.display_name}${p.is_self ? " (self)" : ""}${p.last_activity_at ? ` ${humanTime(p.last_activity_at)}` : ""}`}
              class="min-w-0 flex-1 rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring {selectedId === p.id
                ? 'bg-accent'
                : ''} {p.is_self ? 'font-semibold' : ''}"
              onclick={() => onSelectPerson(p.id)}
            >
              <span class="flex min-w-0 items-start gap-2">
                <PersonAvatar
                  personId={p.id}
                  display_name={p.display_name}
                  photo_cas_hash={p.photo_cas_hash}
                />
                <span class="min-w-0 flex-1">
                  <span class="block truncate">{p.is_self ? `${p.display_name} (self)` : p.display_name}</span>
                  {#if p.last_activity_at || p.preview}
                    <span class="chrome-preview-fg mt-0.5 block truncate text-xs font-normal text-muted-foreground">
                      {humanTime(p.last_activity_at)}{p.last_activity_at && p.preview ? " · " : ""}{p.preview ?? ""}
                    </span>
                  {/if}
                </span>
              </span>
            </button>
            <Button
              variant="ghost"
              size="icon"
              class="size-8 shrink-0"
              tabindex="-1"
              aria-label={`${pinSet.has(p.id) ? t("unpinPerson") : t("pinPerson")} ${p.display_name} ${humanTime(p.last_activity_at)}`}
              onclick={() => onTogglePin(p.id)}
            >
              {#if pinSet.has(p.id)}
                <PinOff class="size-4" />
              {:else}
                <Pin class="size-4" />
              {/if}
            </Button>
          </div>
        {/if}
      </li>
    {/each}
  </ul>
  {#if !sidebarCollapsed}
    {#if peopleLoading}
      <div class="mt-3 min-w-0 space-y-2" aria-hidden="true">
        <Skeleton class="h-4 w-[88%]" />
        <Skeleton class="h-3 w-[64%]" />
        <Skeleton class="h-4 w-[80%]" />
        <Skeleton class="h-3 w-[52%]" />
        <Skeleton class="h-4 w-[72%]" />
        <Skeleton class="h-3 w-[58%]" />
      </div>
    {:else if people.length === 0}
      <div class="mt-3 min-w-0">
        <EmptyState
          title="No people yet"
          body="Import a WhatsApp ZIP or Takeout from the Import tab. Name-only chats become people after import."
          actionLabel="Import"
          onAction={onImport}
        />
      </div>
    {:else if filtered.length === 0}
      <div class="mt-3 min-w-0">
        <EmptyState
          title="No match"
          body="Clear the filter or try another spelling."
          actionLabel="Clear filter"
          onAction={() => (filter = "")}
        />
      </div>
    {/if}
    {#if undoableEvents.length > 0}
      <ul class="mt-3 min-w-0 space-y-1 text-xs">
        {#each undoableEvents as e}
          <li class="flex min-w-0 items-center justify-between gap-2">
            <span class="min-w-0 truncate">{undoRowLabel(e)}</span>
            <Button variant="outline" size="sm" class="shrink-0" tabindex="-1" onclick={() => onUndo(e.id)}>
              undo
            </Button>
          </li>
        {/each}
      </ul>
    {/if}
    <Button variant="outline" size="sm" class="mt-4 max-w-full" tabindex="-1" onclick={onOpenPicker}>
      Open other archive…
    </Button>
  {/if}
</div>
