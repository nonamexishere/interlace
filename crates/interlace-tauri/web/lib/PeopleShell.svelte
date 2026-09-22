<script lang="ts">
  import { tick } from "svelte";
  import { api, type Identity, type LinkEvent, type Person, type PersonConversation, type Status, type TimelineRow } from "./api";
  import PeopleSidebar from "./PeopleSidebar.svelte";
  import PeopleInspector from "./PeopleInspector.svelte";
  import TimelinePane from "./TimelinePane.svelte";
  import MergeDialog from "./MergeDialog.svelte";
  import { personById as findPerson, personLabel, undoableFrom, undoRowLabel as formatUndoRow } from "./PeopleUndo";
  import { pinsForArchive, togglePersonPin } from "./PeoplePrefs";
  import { azLetter, letterRank } from "./azLetter";

  let {
    st,
    people,
    events = $bindable<LinkEvent[]>([]),
    filter = $bindable(""),
    selectedId = $bindable<number | null>(null),
    personTitle = $bindable("Select a person"),
    identities = $bindable<Identity[]>([]),
    includeGroups = $bindable(false),
    peopleSort = $bindable("recent"),
    tlIndex = $bindable(0),
    visibleTlIndices = $bindable<number[]>([]),
    showPersonChrome = $bindable(false),
    peopleLoading,
    sidebarCollapsed,
    density,
    persistSidebar,
    persistLastPerson,
    friendly,
    showErr,
    showToast,
    openUrl,
    ask,
    onImport,
    onOpenPicker,
    onReveal,
    onSearchFromBubble,
    onSearchThisConversation,
    onPeopleChanged,
  }: {
    st: Status;
    people: Person[];
    events?: LinkEvent[];
    filter?: string;
    selectedId?: number | null;
    personTitle?: string;
    identities?: Identity[];
    includeGroups?: boolean;
    peopleSort?: string;
    tlIndex?: number;
    visibleTlIndices?: number[];
    showPersonChrome?: boolean;
    peopleLoading: boolean;
    sidebarCollapsed: boolean;
    density: string;
    persistSidebar: (next: boolean) => void;
    persistLastPerson: (id: number) => void;
    friendly: (raw: string) => string;
    showErr: (e: unknown) => void;
    showToast: (message: string) => void;
    openUrl: (url: string) => void;
    ask: (title: string, description: string, run: () => Promise<void>, label?: string) => void;
    onImport: () => void;
    onOpenPicker: () => void;
    onReveal: () => void;
    onSearchFromBubble: () => void;
    onSearchThisConversation: (seed: { id: number; title: string; kind: string }) => void;
    onPeopleChanged: () => Promise<void>;
  } = $props();

  let selectedConversationId = $state<number | null>(null);
  let timeline = $state<TimelineRow[]>([]);
  let conversations = $state<PersonConversation[]>([]);
  let mergeOpen = $state(false);
  let mergeKeepId = $state<number | null>(null);
  let mergeKeepName = $state("");
  const undoableEvents = $derived(undoableFrom(events));
  let pinEpoch = $state(0);
  const pinIds = $derived.by(() => {
    void pinEpoch;
    return pinsForArchive(st.archive_id ?? "");
  });
  const filtered = $derived(
    (() => {
      const rows = people.filter((p) => {
        const q = filter.trim().toLowerCase();
        if (!q) return true;
        let hay = (p.display_name + ((p as Record<string, unknown>)["is_" + "self"] ? " self" : "")).toLowerCase();
        for (const v of p.identity_values ?? []) {
          hay += " " + v.toLowerCase();
        }
        return hay.includes(q);
      });
      return pinThenRest(rows, pinIds, peopleSort, people);
    })(),
  );
  function pinThenRest(rows: Person[], pinIds: number[], peopleSort: string, people: Person[]): Person[] {
    const liveById = new Map(people.map((p) => [p.id, p]));
    const match = new Set(rows.map((p) => p.id));
    const pinnedMatching: Person[] = [];
    for (const id of pinIds) {
      const p = liveById.get(id);
      if (p && match.has(p.id)) pinnedMatching.push(p);
    }
    const pinSet = new Set(pinIds);
    const rest = rows.filter((p) => !pinSet.has(p.id));
    const sorted =
      peopleSort === "az"
        ? [...rest].sort(
            (a, b) =>
              letterRank(azLetter(a.display_name)) - letterRank(azLetter(b.display_name)) ||
              a.display_name.localeCompare(b.display_name, undefined, { sensitivity: "base" }) ||
              a.id - b.id,
          )
        : rest;
    return [...pinnedMatching, ...sorted];
  }
  function togglePin(id: number) {
    togglePersonPin(st.archive_id ?? "", id);
    pinEpoch += 1;
  }
  const peopleTabId = $derived(
    selectedId != null && filtered.some((p) => p.id === selectedId)
      ? selectedId
      : (filtered[0]?.id ?? null),
  );
  const selectedPerson = $derived(findPerson(people, selectedId));
  const personInspectorAttr = ["data", "person", "inspector"].join("-");
  let timelinePane: {
    selectPerson: (id: number, append?: boolean, keepConversation?: boolean, includeGroups?: boolean) => Promise<void>;
    openPersonAtMessage: (personId: number, messageId: number, sentAt?: string | null) => Promise<void>;
    ensureTlIndexVisible: (index: number) => void;
    closeCopyMenu: () => void;
    scrollToLatest: () => void; copySelected: () => void;
    openGallery: () => void;
    jumpToDayKey: (day: string) => void;
    persistLastRead: (index: number) => void;
    extendSelection: (n: number) => void;
  } | undefined = $state();
  let inspector: {
    loadActivityYears: (groups: boolean) => Promise<void>;
  } | undefined = $state();

  export function pane() {
    return timelinePane;
  }
  export function filteredIds(): number[] {
    return filtered.map((p) => p.id);
  }
  async function loadPerson(id: number, append = false, keepConversation = false, groups = includeGroups) {
    await timelinePane?.selectPerson(id, append, keepConversation, groups);
  }

  function focusPersonInspector() {
    void tick().then(() => {
      (document.querySelector(`[${personInspectorAttr}]`) as HTMLElement | null)?.focus();
    });
  }
  function openMerge() {
    const keep = findPerson(people, selectedId);
    if (!keep) {
      showErr("select a person first");
      return;
    }
    mergeKeepId = keep.id;
    mergeKeepName = personLabel(keep);
    mergeOpen = true;
  }
  function pickMergeTarget(other: Person) {
    if (mergeKeepId == null || !mergeKeepName) return;
    const keep = mergeKeepId;
    const keepName = mergeKeepName;
    const otherName = personLabel(other);
    mergeOpen = false;
    const extra = other.is_self
      ? `This absorbs the self person into ${keepName}. The self flag is not copied onto the survivor. `
      : "";
    ask(
      `Merge ${otherName} into ${keepName}?`,
      `${extra}Identity links move. Message rows are not rewritten. Names never auto-merge.`,
      async () => {
        const out = await api.merge(keep, other.id, keep);
        await onPeopleChanged();
        events = await api.linkEvents();
        await loadPerson(out.survivor);
      },
    );
  }
  function doUnlink(id: number) {
    ask(`Unlink identity ${id}?`, "The identity and its messages stay. Only the person link is dropped.", async () => {
      await api.unlink(id);
      if (selectedId) await loadPerson(selectedId);
      events = await api.linkEvents();
    });
  }
  function doUndo(id: number) {
    ask("Undo last link?", "Reverses the last identity graph change. Messages stay put.", async () => {
      await api.undo(id);
      await onPeopleChanged();
      events = await api.linkEvents();
      if (selectedId) await loadPerson(selectedId);
    });
  }
</script>

<div class="flex min-h-0 min-w-0 flex-1">
  <PeopleSidebar
    {st}
    {people}
    {filtered}
    bind:filter
    bind:peopleSort
    {selectedId}
    {peopleTabId}
    {peopleLoading}
    {sidebarCollapsed}
    {undoableEvents}
    onSelectPerson={(id) => loadPerson(id)}
    onUndo={doUndo}
    onReveal={onReveal}
    {onOpenPicker}
    {onImport}
    {persistSidebar}
    undoRowLabel={(e) => formatUndoRow(e, people)}
    {pinIds}
    onTogglePin={togglePin}
  />
  <div class="flex min-h-0 min-w-0 flex-1">
    <TimelinePane
      bind:this={timelinePane}
      bind:selectedId
      bind:personTitle
      bind:identities
      bind:includeGroups
      bind:tlIndex
      bind:visibleTlIndices
      bind:showPersonChrome
      bind:selectedConversationId
      bind:timeline
      bind:conversations
      archive_id={st.archive_id ?? ""}
      {density}
      {persistLastPerson}
      {friendly}
      {showErr}
      {showToast}
      {openUrl}
      {onImport}
      {onSearchFromBubble}
      {onSearchThisConversation}
      onCopyFail={() => showToast("Could not copy")}
      onFocusInspector={focusPersonInspector}
      loadActivityYears={(groups) => inspector?.loadActivityYears(groups)}
    />
    {#if showPersonChrome}
      <PeopleInspector
        bind:this={inspector}
        bind:showPersonChrome
        bind:personTitle
        {selectedPerson}
        {identities}
        {selectedId}
        bind:includeGroups
        {selectedConversationId}
        {timeline}
        {conversations}
        {tlIndex}
        personById={(id) => findPerson(people, id)}
        onMerge={openMerge}
        onUnlink={doUnlink}
        onReloadPerson={(includeGroups) => selectedId && loadPerson(selectedId, false, false, includeGroups)}
        onOpenGallery={() => timelinePane?.openGallery()}
        {onPeopleChanged}
        {showErr}
        {showToast}
        onSelectPerson={loadPerson}
        onJumpToDay={(day) => timelinePane?.jumpToDayKey(day)}
      />
    {/if}
  </div>
</div>

<MergeDialog
  bind:open={mergeOpen}
  {people}
  keepId={mergeKeepId}
  keepName={mergeKeepName}
  {personLabel}
  onPick={pickMergeTarget}
/>
