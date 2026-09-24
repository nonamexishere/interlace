<script lang="ts">
  import { onMount, untrack } from "svelte";
  import { fly } from "svelte/transition";
  import {
    api,
    type ConversationParticipantName,
    type Identity,
    type Person,
    type PersonConversation,
    type PersonYearCount,
    type TimelineRow,
  } from "./api";
  import { humanTime } from "./formatTime";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import { t } from "$lib/i18n";
  import { chromeMotionMs } from "$lib/motion";
  import { writeIncludeGroupsPref } from "./PeoplePrefs";
  import PersonAvatar from "./PersonAvatar.svelte";
  import { isMailRow } from "./TimelineMail";

  type YearJump = (day: string) => void;

  let {
    showPersonChrome = $bindable(false),
    personTitle = $bindable(""),
    selectedPerson,
    identities,
    selectedId,
    includeGroups = $bindable(false),
    selectedConversationId = null as number | null,
    timeline = [] as TimelineRow[],
    conversations = [] as PersonConversation[],
    tlIndex = 0,
    personById,
    onMerge,
    onUnlink,
    onReloadPerson,
    onOpenGallery,
    onPeopleChanged,
    showErr,
    showToast,
    onSelectPerson,
    onJumpToDay,
  }: {
    showPersonChrome?: boolean;
    personTitle: string;
    selectedPerson: Person | undefined;
    identities: Identity[];
    selectedId: number | null;
    includeGroups?: boolean;
    selectedConversationId?: number | null;
    timeline?: TimelineRow[];
    conversations?: PersonConversation[];
    tlIndex?: number;
    personById: (id: number | null) => Person | undefined;
    onMerge: () => void;
    onUnlink: (id: number) => void;
    onReloadPerson: (includeGroups: boolean) => void;
    onOpenGallery: () => void;
    onPeopleChanged: () => Promise<void>;
    showErr: (e: unknown) => void;
    showToast: (message: string) => void;
    onSelectPerson: (id: number) => void;
    onJumpToDay: YearJump;
  } = $props();

  let nameDraft = $state("");
  let notesDraft = $state("");
  let notesReady = $state(false);
  let notesLoadGen = 0;

  $effect(() => {
    const id = selectedId;
    const seedName = untrack(() => selectedPerson?.display_name ?? personTitle);
    nameDraft = seedName;
    notesDraft = "";
    notesReady = false;
    if (id == null) {
      notesLoadGen += 1;
      return;
    }
    const gen = ++notesLoadGen;
    const nameAtStart = seedName;
    const notesAtStart = "";
    void api
      .personShow(id)
      .then((show) => {
        if (gen !== notesLoadGen) return;
        notesReady = true;
        if (nameDraft === nameAtStart) nameDraft = show.display_name;
        if (notesDraft === notesAtStart) notesDraft = show.notes ?? "";
      })
      .catch(showErr);
  });

  async function confirmRename() {
    const name = nameDraft.trim();
    if (!name) return;
    if (selectedId == null) return;
    try {
      await api.personRename(selectedId, name);
      await onPeopleChanged();
      const show = await api.personShow(selectedId);
      personTitle = show.display_name;
      nameDraft = show.display_name;
    } catch (e) {
      showErr(e);
    }
  }

  async function saveNotes() {
    if (selectedId == null) return;
    try {
      await api.personSetNotes(selectedId, notesDraft);
      await onPeopleChanged();
      const show = await api.personShow(selectedId);
      notesDraft = show.notes ?? "";
    } catch (e) {
      showErr(e);
    }
  }

  let participants = $state<ConversationParticipantName[]>([]);
  let conversation_kind = $state("");
  let loadGen = 0;

  async function loadGroupParticipants() {
    const gen = ++loadGen;
    if (!includeGroups) {
      if (gen !== loadGen) return;
      participants = [];
      conversation_kind = "";
      return;
    }
    let cid: number | null = null;
    if (selectedConversationId != null) {
      const conv = conversations.find((c) => c.id === selectedConversationId);
      const hit = timeline.find((r) => r.conversation_id === selectedConversationId);
      if (conv?.kind === "group" || hit?.conversation_kind === "group") {
        cid = selectedConversationId;
      }
    } else {
      const row = timeline[tlIndex];
      if (row?.conversation_kind === "group") cid = row.conversation_id;
    }
    if (gen !== loadGen) return;
    conversation_kind = cid != null ? "group" : "";
    if (cid == null) {
      participants = [];
      return;
    }
    try {
      const names = await api.conversationParticipants(cid);
      if (gen !== loadGen) return;
      participants = names;
    } catch {
      if (gen !== loadGen) return;
      participants = [];
    }
  }

  $effect(() => {
    void selectedConversationId;
    void timeline;
    void conversations;
    void tlIndex;
    void loadGroupParticipants();
  });

  let inspectorEl = $state<HTMLElement | undefined>(undefined);

  $effect(() => {
    void timeline[tlIndex]?.message_id;
    inspectorEl?.scrollTo(0, 0);
  });

  function openParticipant(person_id: number | null) {
    if (person_id == null) {
      showToast(t("noLivePerson"));
      return;
    }
    if (person_id === selectedId) return;
    onSelectPerson(person_id);
  }

  let years = $state<PersonYearCount[]>([]);
  let yearsLoading = $state(false);
  let yearsError = $state(false);
  let yearsGen = 0;

  export async function loadActivityYears(groups: boolean) {
    const gen = ++yearsGen;
    years = [];
    yearsError = false;
    yearsLoading = true;
    if (selectedId == null) {
      yearsLoading = false;
      return;
    }
    try {
      const rows = await api.personYearCounts({
        id: selectedId,
        includeGroups: groups,
      });
      if (gen !== yearsGen) return;
      years = rows;
      yearsLoading = false;
    } catch {
      if (gen !== yearsGen) return;
      years = [];
      yearsError = true;
      yearsLoading = false;
    }
  }

  onMount(() => {
    void loadActivityYears(includeGroups);
  });
</script>

{#if showPersonChrome}
<aside
  data-person-inspector
  bind:this={inspectorEl}
  tabindex="-1"
  class="flex w-72 shrink-0 flex-col gap-3 overflow-y-auto border-l border-border p-4 text-sm"
  aria-label={t("inspector")}
  transition:fly={{ x: 16, duration: chromeMotionMs() }}
>
  <div class="flex min-w-0 items-center gap-2">
    <button
      type="button"
      class="min-w-0 flex-1 text-left font-medium focus-visible:ring-2 focus-visible:ring-ring"
      onclick={() => (showPersonChrome = !showPersonChrome)}
    >{personTitle}</button>
    <PersonAvatar personId={selectedPerson?.id ?? selectedId ?? 0} display_name={selectedPerson?.display_name ?? personTitle} photo_cas_hash={selectedPerson?.photo_cas_hash} />
  </div>
  <p class="text-xs text-muted-foreground">
    {t("lastActivity")}
    {humanTime(selectedPerson?.last_activity_at)}
  </p>
  {#if yearsLoading || yearsError || years.length}
    <div data-activity-years class="flex flex-col items-start gap-1" aria-busy={yearsLoading}>
      {#if yearsLoading}
        <Skeleton class="h-3 w-24" />
        <Skeleton class="h-3 w-16" />
      {:else if yearsError}
        <p class="text-xs text-muted-foreground">{t("activityYearsFailed")}</p>
        <button
          type="button"
          class="text-left text-xs text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
          onclick={() => void loadActivityYears(includeGroups)}
        >{t("activityYearsRetry")}</button>
      {:else}
        <p class="text-xs font-medium">{t("activityYears")}</p>
        {#each years as row (row.year)}
          <button
            type="button"
            data-activity-year
            class="flex w-full items-baseline justify-between text-left text-xs text-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
            onclick={() => onJumpToDay(row.first_local_day)}
          >
            {row.year}
            <span class="tabular-nums text-muted-foreground">{row.count} {t("activityYearMessages")}</span>
          </button>
        {/each}
      {/if}
    </div>
  {/if}
  {#if timeline[tlIndex] && isMailRow(timeline[tlIndex])}
    {@const rec = timeline[tlIndex].recipients}
    {#if rec && (rec.to.length || rec.cc.length || rec.bcc.length)}
      <div data-mail-recipients class="space-y-2">
        {#if rec.to.length}
          <div>
            <p class="text-xs font-medium">{t("mailTo")}</p>
            <ul class="space-y-1 text-sm text-muted-foreground">
              {#each rec.to as name}
                <li>{name}</li>
              {/each}
            </ul>
          </div>
        {/if}
        {#if rec.cc.length}
          <div>
            <p class="text-xs font-medium">{t("mailCc")}</p>
            <ul class="space-y-1 text-sm text-muted-foreground">
              {#each rec.cc as name}
                <li>{name}</li>
              {/each}
            </ul>
          </div>
        {/if}
        {#if rec.bcc.length}
          <div>
            <p class="text-xs font-medium">{t("mailBcc")}</p>
            <ul class="space-y-1 text-sm text-muted-foreground">
              {#each rec.bcc as name}
                <li>{name}</li>
              {/each}
            </ul>
          </div>
        {/if}
      </div>
    {/if}
  {/if}
  <div class="flex flex-col gap-2">
    <div class="flex items-center gap-2">
      <Input
        bind:value={nameDraft}
        aria-label={t("personName")}
        disabled={selectedId == null}
        class="h-8 min-w-0"
        onkeydown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            void confirmRename();
          }
        }}
      />
      <Button
        variant="outline"
        size="sm"
        data-person-rename-confirm
        disabled={selectedId == null}
        onclick={() => void confirmRename()}>{t("renameConfirm")}</Button
      >
    </div>
    <div class="flex flex-col gap-2">
      <Input
        bind:value={notesDraft}
        aria-label={t("personNotes")}
        disabled={selectedId == null}
        class="h-8 min-w-0"
      />
      <Button
        variant="outline"
        size="sm"
        data-person-notes-save
        disabled={!notesReady}
        onclick={() => void saveNotes()}>{t("saveNotes")}</Button
      >
    </div>
    <Button variant="outline" size="sm" disabled={!personById(selectedId)} onclick={onMerge}
      >Merge…</Button
    >
    <Button
      variant="outline"
      size="sm"
      data-person-gallery-open
      disabled={selectedId == null}
      onclick={onOpenGallery}>{t("media")}</Button
    >
    <label class="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        class="focus-visible:ring-2 focus-visible:ring-ring"
        bind:checked={includeGroups}
        onchange={() => {
          writeIncludeGroupsPref(includeGroups);
          onReloadPerson(includeGroups);
          void loadActivityYears(includeGroups);
        }}
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
  {#if includeGroups && conversation_kind === "group"}
    <p class="text-xs font-medium">{t("inThisGroup")}</p>
    <ul data-group-participants class="space-y-1 text-sm text-muted-foreground">
      {#each participants as participant (participant.identity_id)}
        <li>
          <button
            type="button"
            class="text-left focus-visible:ring-2 focus-visible:ring-ring"
            onclick={() => openParticipant(participant.person_id)}
          >
            {participant.display_name || participant.value}{#if personById(participant.person_id)?.is_self} {t("self")}{/if}
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</aside>
{/if}
