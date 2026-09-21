<script lang="ts">
  import { onMount } from "svelte";
  import { api, type LabelRef, type Person, type SearchHit } from "./api";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Label } from "$lib/components/ui/label/index.js";
  import SearchHits from "./SearchHits.svelte";
  import { t } from "./i18n";

  let {
    people,
    archivePath,
    onError,
    onToast,
    onJumpToMessage,
    friendly,
    q = $bindable(),
    seedPerson = null,
    seedConversation = null,
  }: {
    people: Person[];
    archivePath: string;
    onError: (e: unknown) => void;
    onToast?: (message: string) => void;
    friendly: (raw: string) => string;
    onJumpToMessage: (args: {
      personId: number;
      messageId: number;
      conversationKind?: string | null;
      sentAt?: string | null;
    }) => void | Promise<void>;
    q?: string;
    seedPerson?: Person | null;
    seedConversation?: { id: number; title: string; kind: string } | null;
  } = $props();
  /** Stored person_id for api.search; null when cleared / no pick. */
  let personId = $state<number | null>(null);
  let personFilter = $state("");
  let personListOpen = $state(false);
  let personHighlight = $state(0);
  let from = $state("");
  let to = $state("");
  let platform = $state("");
  let conversationKind = $state("");
  let attachmentFilter = $state("");
  let labelId = $state("");
  let labels = $state<LabelRef[]>([]);
  let includeGroups = $state(false);
  let conversationId = $state<number | null>(null);
  let conversationTitle = $state("");
  let hits = $state<SearchHit[]>([]);
  /** Highlighted hit in the results list (j/k and arrow keys). */
  let hitIndex = $state(0);
  let previewBody = $state("");
  let previewMessageId = $state<number | null>(null);
  let previewGen = 0;
  let empty = $state(false);
  let searched = $state(false);
  let searching = $state(false);
  let searchError = $state("");
  let searchGen = 0;
  let labelsGen = 0;

  type DatePresetKind = "7d" | "30d" | "year" | "any";

  function localYmd(d: Date): string {
    const y = d.getFullYear();
    const m = d.getMonth() + 1;
    const day = d.getDate();
    return `${y}-${String(m).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  }

  function datePresetWindow(kind: DatePresetKind) {
    if (kind === "any") {
      const from = "";
      const to = "";
      return { from, to };
    }
    const d = new Date();
    const today = localYmd(d);
    if (kind === "7d") {
      const start = new Date();
      start.setDate(start.getDate() - 6);
      return { from: localYmd(start), to: today };
    }
    if (kind === "30d") {
      const start = new Date();
      start.setDate(start.getDate() - 29);
      return { from: localYmd(start), to: today };
    }
    return { from: `${d.getFullYear()}-01-01`, to: today };
  }

  function isPresetPressed(kind: DatePresetKind): boolean {
    const w = datePresetWindow(kind);
    return from === w.from && to === w.to;
  }

  function applyDatePreset(kind: DatePresetKind) {
    const w = datePresetWindow(kind);
    from = w.from;
    to = w.to;
    cancelDebounce();
    if (!q.trim()) {
      clearHitsIdle();
      return;
    }
    void run();
  }

  function personLabel(p: Person) {
    return p.is_self ? `${p.display_name} (self)` : p.display_name;
  }

  const filteredPeople = $derived(
    people.filter((p) => {
      const needle = personFilter.trim().toLowerCase();
      if (!needle) return true;
      const hay = (p.display_name + (p.is_self ? " self" : "")).toLowerCase();
      return hay.includes(needle);
    }),
  );

  function pickPerson(p: Person) {
    personId = p.id;
    personFilter = personLabel(p);
    personListOpen = false;
  }

  $effect(() => {
    if (seedPerson) {
      pickPerson(seedPerson);
    }
  });

  $effect(() => {
    if (seedConversation) {
      conversationId = seedConversation.id;
      conversationTitle = seedConversation.title;
      if (seedConversation.kind === "group") {
        includeGroups = true;
      }
    }
  });

  $effect(() => {
    if (personId == null) return;
    const p = people.find((x) => x.id === personId);
    if (p) personFilter = personLabel(p);
  });

  function clearPerson() {
    personId = null;
    personFilter = "";
    personHighlight = 0;
    personListOpen = false;
  }

  function clearConversation() {
    conversationId = null;
    conversationTitle = "";
    if (!q.trim()) {
      clearHitsIdle();
      return;
    }
    void run();
  }

  let personBlurCloseTimer: ReturnType<typeof setTimeout> | null = null;
  /** One debounce timer for type-to-search; run() clears it so submit cannot double-fire. */
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;

  function cancelPersonBlurClose() {
    if (personBlurCloseTimer != null) {
      clearTimeout(personBlurCloseTimer);
      personBlurCloseTimer = null;
    }
  }

  function cancelDebounce() {
    if (debounceTimer != null) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
  }

  function onPersonFilterInput() {
    // Typing invalidates a previous pick so search does not keep a stale id.
    personId = null;
    personListOpen = true;
    personHighlight = 0;
  }

  function onPersonFocus() {
    cancelPersonBlurClose();
    personListOpen = true;
  }

  /** Close list after blur; delay so option mousedown can pick first. */
  function onPersonBlur() {
    cancelPersonBlurClose();
    personBlurCloseTimer = setTimeout(() => {
      personListOpen = false;
      personBlurCloseTimer = null;
    }, 150);
  }

  function onPersonKeydown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      e.stopPropagation();
      // Need a name query so Enter does not grab the first of the full list.
      if (!personFilter.trim()) return;
      const list = filteredPeople;
      if (list.length > 0) {
        const idx = Math.min(Math.max(0, personHighlight), list.length - 1);
        pickPerson(list[idx]);
      }
      return;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      clearPerson();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      personListOpen = true;
      if (filteredPeople.length > 0) {
        personHighlight = Math.min(personHighlight + 1, filteredPeople.length - 1);
      }
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      personHighlight = Math.max(personHighlight - 1, 0);
    }
  }

  function clearPreview() {
    previewBody = "";
    previewMessageId = null;
    previewGen += 1;
  }

  async function fillPreview(h: SearchHit | undefined) {
    if (!h) {
      clearPreview();
      return;
    }
    previewMessageId = h.message_id;
    previewBody = "";
    const gen = ++previewGen;
    const id = h.message_id;
    try {
      const got = await api.searchBody(id);
      if (gen !== previewGen || id !== previewMessageId) return;
      previewBody = got;
    } catch (e) {
      if (gen !== previewGen || id !== previewMessageId) return;
      previewBody = "";
      onError(e);
    }
  }

  async function run() {
    if (!q.trim()) {
      clearHitsIdle();
      return;
    }
    cancelDebounce();
    const gen = ++searchGen;
    empty = false;
    searched = true;
    searching = true;
    searchError = "";
    previewBody = "";
    previewMessageId = null;
    previewGen += 1;
    const fromRaw = from.trim();
    const toRaw = to.trim();
    const fromDate = fromRaw ? Date.parse(fromRaw) : Number.NaN;
    const toDate = toRaw ? Date.parse(toRaw) : Number.NaN;
    if (
      (fromRaw && Number.isNaN(fromDate)) ||
      (toRaw && Number.isNaN(toDate)) ||
      (fromRaw && toRaw && fromDate > toDate)
    ) {
      searchError = t("searchDateInvalid");
      searching = false;
      hits = [];
      hitIndex = 0;
      return;
    }
    if (labelId && !labels.some((lab) => String(lab.id) === String(labelId))) {
      searchError = t("searchLabelInvalid");
      searching = false;
      hits = [];
      hitIndex = 0;
      return;
    }
    try {
      const next = await api.search({
        q: q.trim(),
        personId: personId != null ? personId : null,
        conversationId: conversationId,
        from: from.trim() || null,
        to: !to.trim() ? null : to.trim() + "T23:59:59",
        platform: platform || null,
        conversationKind: conversationKind || null,
        attachmentFilter: attachmentFilter || null,
        labelId: labelId ? Number(labelId) : null,
        includeGroups: includeGroups,
        limit: 50,
      });
      if (gen !== searchGen) return;
      hits = next;
      empty = hits.length === 0;
      hitIndex = 0;
      if (hits[0]) void fillPreview(hits[0]);
      else clearPreview();
    } catch (e) {
      if (gen === searchGen) {
        searchError = friendly(e instanceof Error ? e.message : String(e ?? ""));
        hits = [];
        hitIndex = 0;
        clearPreview();
      }
    } finally {
      if (gen === searchGen) searching = false;
    }
  }

  function clearHitsIdle() {
    searchGen += 1;
    hits = [];
    empty = false;
    searched = false;
    searching = false;
    searchError = "";
    hitIndex = 0;
    clearPreview();
  }

  // Only `q` is read so filters stay submit-only.
  $effect(() => {
    const query = q;
    if (!query.trim()) {
      clearHitsIdle();
      return;
    }
    cancelDebounce();
    debounceTimer = setTimeout(() => {
      debounceTimer = null;
      void run();
    }, 200);
    return () => cancelDebounce();
  });

  /** With person_id → People timeline at that message; else stay on Search preview. */
  function activateHit(h: SearchHit) {
    if (h.person_id != null) {
      void onJumpToMessage({
        personId: h.person_id,
        messageId: h.message_id,
        conversationKind: h.conversation_kind,
        sentAt: h.sent_at,
      });
    }
  }

  function scrollHitIntoView(i: number) {
    requestAnimationFrame(() => {
      document
        .querySelector(`[data-search-hit="${i}"]`)
        ?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    });
  }

  function onHitsKey(e: KeyboardEvent) {
    const t = e.target as HTMLElement | null;
    if (
      t &&
      (t.tagName === "INPUT" ||
        t.tagName === "TEXTAREA" ||
        t.tagName === "SELECT" ||
        t.tagName === "SUMMARY" ||
        t.closest("[data-search-filters]"))
    ) {
      return;
    }
    if (!hits.length) return;
    if (e.key === " ") {
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    if (e.key === "j" || e.key === "ArrowDown") {
      e.preventDefault();
      e.stopPropagation();
      if (hitIndex < hits.length - 1) {
        hitIndex += 1;
        scrollHitIntoView(hitIndex);
        void fillPreview(hits[hitIndex]);
      }
      return;
    }
    if (e.key === "k" || e.key === "ArrowUp") {
      e.preventDefault();
      e.stopPropagation();
      if (hitIndex > 0) {
        hitIndex -= 1;
        scrollHitIntoView(hitIndex);
        void fillPreview(hits[hitIndex]);
      }
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      e.stopPropagation();
      const h = hits[hitIndex];
      if (h) activateHit(h);
    }
  }

  async function loadLabels(gen: number) {
    try {
      const next = await api.labelsList();
      if (gen !== labelsGen) return;
      labels = next;
    } catch {
      if (gen !== labelsGen) return;
      labels = [];
    }
  }

  $effect(() => {
    void archivePath;
    const gen = ++labelsGen;
    labelId = "";
    labels = [];
    void loadLabels(gen);
  });

  onMount(() => {
    window.addEventListener("keydown", onHitsKey);
    // Close person list when clicking outside the combobox.
    const onPointerDown = (e: PointerEvent) => {
      const root = document.querySelector("[data-person-picker]");
      if (!root || !(e.target instanceof Node)) return;
      if (!root.contains(e.target)) {
        cancelPersonBlurClose();
        personListOpen = false;
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      window.removeEventListener("keydown", onHitsKey);
      document.removeEventListener("pointerdown", onPointerDown);
      cancelPersonBlurClose();
    };
  });
</script>

<div class="flex min-h-0 min-w-0 flex-1 flex-col p-4">
  <h1 class="mb-3 text-xl font-semibold tracking-tight">Search</h1>
  <form
    class="mb-4 shrink-0 space-y-3"
    onsubmit={(e) => {
      e.preventDefault();
      run();
    }}
  >
    <div class="space-y-1.5">
      <Label for="q">Query</Label>
      <Input id="q" bind:value={q} placeholder="FTS — same as CLI search" />
      {#if conversationId != null}
        <div
          class="flex min-w-0 items-center gap-2 rounded-md border border-border bg-muted/40 px-2 py-1 text-sm"
          data-search-conversation
        >
          <span class="min-w-0 truncate">{conversationTitle}</span>
          <button
            type="button"
            class="shrink-0 text-xs text-muted-foreground underline focus-visible:ring-2 focus-visible:ring-ring"
            onclick={clearConversation}
          >
            Clear
          </button>
        </div>
      {/if}
    </div>
    <details
      data-search-filters
      class="rounded-md border border-border bg-muted/40 px-3 py-2"
    >
      <summary class="cursor-pointer text-xs font-medium text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring">
        {t("searchFilters")}
      </summary>
      <div class="mt-3 grid gap-3 sm:grid-cols-2">
        <div class="space-y-1.5" data-person-picker>
          <Label for="sp">Person</Label>
          <div class="relative">
            <Input
              id="sp"
              bind:value={personFilter}
              placeholder="Messages with…"
              role="combobox"
              aria-autocomplete="list"
              aria-expanded={personListOpen}
              aria-controls="person-options"
              autocomplete="off"
              class={personId != null ? "pr-14" : undefined}
              oninput={onPersonFilterInput}
              onfocus={onPersonFocus}
              onblur={onPersonBlur}
              onkeydown={onPersonKeydown}
            />
            {#if personId != null}
              <button
                type="button"
                class="absolute top-1/2 right-2 -translate-y-1/2 text-xs text-muted-foreground underline focus-visible:ring-2 focus-visible:ring-ring"
                onclick={clearPerson}
              >
                Clear
              </button>
            {/if}
            {#if personListOpen && personFilter.trim() && filteredPeople.length > 0 && personId == null}
              <ul
                id="person-options"
                role="listbox"
                class="person-options absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-md border border-border bg-background py-1 shadow-md"
                onmousedown={(e) => e.preventDefault()}
              >
                {#each filteredPeople as p, i}
                  <li>
                    <button
                      type="button"
                      role="option"
                      aria-selected={i === personHighlight}
                      class="w-full px-3 py-1.5 text-left text-sm hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring {i === personHighlight
                        ? 'bg-accent'
                        : ''}"
                      onclick={() => pickPerson(p)}
                    >
                      {p.display_name}{#if p.is_self}
                        {" "}(self){/if}
                    </button>
                  </li>
                {/each}
              </ul>
            {/if}
          </div>
          {#if personId != null}
            <p class="text-xs text-muted-foreground">Messages with {personFilter}</p>
          {/if}
        </div>
        <div class="space-y-1.5">
          <Label for="plat">Platform</Label>
          <select
            id="plat"
            bind:value={platform}
            class="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="">Any</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="gmail">Gmail</option>
            <option value="contacts">Contacts</option>
          </select>
        </div>
        <div class="space-y-1.5">
          <Label for="skind">Kind</Label>
          <select
            id="skind"
            bind:value={conversationKind}
            class="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="">Any</option>
            <option value="dm">DM</option>
            <option value="group">Group</option>
            <option value="email_thread">Email thread</option>
          </select>
        </div>
        <div class="space-y-1.5">
          <Label for="satt">Attachment</Label>
          <select
            id="satt"
            bind:value={attachmentFilter}
            class="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="">Any</option>
            <option value="has_file">Has file</option>
            <option value="omitted">Omitted</option>
            <option value="missing">Missing</option>
          </select>
        </div>
        <div class="space-y-1.5">
          <Label for="slabel">{t("searchLabel")}</Label>
          <select
            id="slabel"
            data-gmail-label
            bind:value={labelId}
            class="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="">{t("searchLabelAny")}</option>
            {#each labels as lab}
              <option value={String(lab.id)}>{lab.name}</option>
            {/each}
          </select>
        </div>
        <div class="space-y-1.5">
          <Label for="from">{t("searchFrom")}</Label>
          <Input id="from" type={"date"} bind:value={from} />
        </div>
        <div class="space-y-1.5">
          <Label for="to">{t("searchTo")}</Label>
          <Input id="to" type={"date"} bind:value={to} />
        </div>
        <div class="flex flex-wrap gap-1.5 sm:col-span-2">
          <Button type="button" size="sm" variant={isPresetPressed("7d") ? "secondary" : "outline"} aria-pressed={isPresetPressed("7d")} onclick={() => applyDatePreset("7d")}>{t("searchLast7Days")}</Button>
          <Button type="button" size="sm" variant={isPresetPressed("30d") ? "secondary" : "outline"} aria-pressed={isPresetPressed("30d")} onclick={() => applyDatePreset("30d")}>{t("searchLast30Days")}</Button>
          <Button type="button" size="sm" variant={isPresetPressed("year") ? "secondary" : "outline"} aria-pressed={isPresetPressed("year")} onclick={() => applyDatePreset("year")}>{t("searchThisYear")}</Button>
          <Button type="button" size="sm" variant={isPresetPressed("any") ? "secondary" : "outline"} aria-pressed={isPresetPressed("any")} onclick={() => applyDatePreset("any")}>{t("searchAnyDate")}</Button>
        </div>
        <label class="flex items-center gap-2 text-sm sm:col-span-2">
          <input type="checkbox" class="focus-visible:ring-2 focus-visible:ring-ring" bind:checked={includeGroups} />
          include groups
        </label>
      </div>
    </details>
    <Button type="submit" disabled={searching}>{searching ? "Searching…" : "Search"}</Button>
  </form>

  <SearchHits
    {hits}
    bind:hitIndex
    {previewBody}
    {previewMessageId}
    {searching}
    {searched}
    {searchError}
    {empty}
    onRetry={run}
    onActivate={(h, i) => {
      hitIndex = i;
      void fillPreview(h);
    }}
    {onToast}
  />
</div>
