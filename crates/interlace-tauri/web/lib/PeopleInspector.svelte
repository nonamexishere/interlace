<script lang="ts">
  import { untrack } from "svelte";
  import { fly } from "svelte/transition";
  import {
    api,
    type ConversationParticipantName,
    type Identity,
    type Person,
    type PersonConversation,
    type TimelineRow,
  } from "./api";
  import { humanTime } from "./formatTime";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { t } from "$lib/i18n";
  import { chromeMotionMs } from "$lib/motion";
  import { writeIncludeGroupsPref } from "./PeoplePrefs";
  import PersonAvatar from "./PersonAvatar.svelte";

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
</script>

{#if showPersonChrome}
<aside
  data-person-inspector
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
  {#if includeGroups && conversation_kind === "group"}
    <p class="text-xs font-medium">{t("inThisGroup")}</p>
    <ul data-group-participants class="space-y-1 text-sm text-muted-foreground">
      {#each participants as participant}
        <li>{participant.display_name || participant.value}</li>
      {/each}
    </ul>
  {/if}
</aside>
{/if}
