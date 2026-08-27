<script lang="ts">
  import { tick } from "svelte";
  import { api, type Identity, type LinkEvent, type Person, type Status } from "./api";
  import PeopleSidebar from "./PeopleSidebar.svelte";
  import PeopleInspector from "./PeopleInspector.svelte";
  import TimelinePane from "./TimelinePane.svelte";
  import MergeDialog from "./MergeDialog.svelte";
  import { personById as findPerson, personLabel, undoableFrom, undoRowLabel as formatUndoRow } from "./PeopleUndo";

  let {
    st,
    people,
    events = $bindable<LinkEvent[]>([]),
    filter = $bindable(""),
    selectedId = $bindable<number | null>(null),
    personTitle = $bindable("Select a person"),
    identities = $bindable<Identity[]>([]),
    includeGroups = $bindable(false),
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
    onPeopleChanged: () => Promise<void>;
  } = $props();

  let mergeOpen = $state(false);
  let mergeKeepId = $state<number | null>(null);
  let mergeKeepName = $state("");
  const undoableEvents = $derived(undoableFrom(events));
  const filtered = $derived(
    people.filter((p) => {
      const q = filter.trim().toLowerCase();
      if (!q) return true;
      let hay = (p.display_name + (p.is_self ? " self" : "")).toLowerCase();
      for (const v of p.identity_values ?? []) {
        hay += " " + v.toLowerCase();
      }
      return hay.includes(q);
    }),
  );
  const peopleTabId = $derived(
    selectedId != null && filtered.some((p) => p.id === selectedId)
      ? selectedId
      : (filtered[0]?.id ?? null),
  );
  const selectedPerson = $derived(findPerson(people, selectedId));
  const personInspectorAttr = ["data", "person", "inspector"].join("-");
  let timelinePane: {
    selectPerson: (id: number, append?: boolean, keepConversation?: boolean) => Promise<void>;
    openPersonAtMessage: (personId: number, messageId: number, sentAt?: string | null) => Promise<void>;
    ensureTlIndexVisible: (index: number) => void;
    closeCopyMenu: () => void;
  } | undefined = $state();

  export function pane() {
    return timelinePane;
  }
  export function filteredIds(): number[] {
    return filtered.map((p) => p.id);
  }
  async function loadPerson(id: number, append = false, keepConversation = false) {
    await timelinePane?.selectPerson(id, append, keepConversation);
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
      {density}
      {persistLastPerson}
      {friendly}
      {showErr}
      {showToast}
      {openUrl}
      {onImport}
      {onSearchFromBubble}
      onCopyFail={() => showToast("Could not copy")}
      onFocusInspector={focusPersonInspector}
    />
    {#if showPersonChrome}
      <PeopleInspector
        bind:showPersonChrome
        {personTitle}
        {selectedPerson}
        {identities}
        {selectedId}
        bind:includeGroups
        personById={(id) => findPerson(people, id)}
        onMerge={openMerge}
        onUnlink={doUnlink}
        onReloadPerson={() => selectedId && loadPerson(selectedId)}
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
