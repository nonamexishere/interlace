<script lang="ts">
  import * as Command from "$lib/components/ui/command/index.js";
  import type { Person } from "./api";

  const PALETTE_PEOPLE_CAP = 32;

  let {
    people,
    personLabel,
    onView,
    onPerson,
    onClose,
  }: {
    people: Person[];
    personLabel: (p: Person) => string;
    onView: (next: "people" | "search" | "review" | "import" | "doctor") => void;
    onPerson: (p: Person) => void;
    onClose: () => void;
  } = $props();

  let query = $state("");

  function selectedText(el: HTMLInputElement): string {
    const a = el.selectionStart ?? 0;
    const b = el.selectionEnd ?? 0;
    return el.value.slice(a, b);
  }

  function replaceSelection(el: HTMLInputElement, insert: string) {
    const a = el.selectionStart ?? 0;
    const b = el.selectionEnd ?? 0;
    const next = el.value.slice(0, a) + insert + el.value.slice(b);
    el.value = next;
    const caret = a + insert.length;
    el.setSelectionRange(caret, caret);
    el.dispatchEvent(new InputEvent("input", { bubbles: true }));
  }

  function onPaletteFieldKey(e: KeyboardEvent) {
    const el = e.currentTarget;
    if (!(el instanceof HTMLInputElement)) return;
    const fieldMod = e.metaKey || (e.ctrlKey && !e.altKey);
    if (!fieldMod) return;
    const key = e.key;
    if (key === "a" || key === "A") {
      e.preventDefault();
      e.stopPropagation();
      el.select();
      return;
    }
    if ((key === "c" || key === "C") && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      e.stopPropagation();
      const text = selectedText(el);
      if (text) void navigator.clipboard.writeText(text);
      return;
    }
    if ((key === "x" || key === "X") && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      e.stopPropagation();
      const text = selectedText(el);
      if (text) {
        void navigator.clipboard.writeText(text);
        replaceSelection(el, "");
      }
      return;
    }
    if ((key === "v" || key === "V") && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      e.stopPropagation();
      void navigator.clipboard.readText().then((clip) => {
        replaceSelection(el, clip);
      }).catch(() => {});
    }
  }

  const palettePeople = $derived(
    people
      .filter((p) => {
        const needle = query.trim().toLowerCase();
        if (!needle) return true;
        const hay = (p.display_name + (p.is_self ? " self" : "")).toLowerCase();
        return hay.includes(needle);
      })
      .slice(0, PALETTE_PEOPLE_CAP),
  );
</script>

<div
  class="fixed inset-0 z-[100] flex items-start justify-center bg-background/80 pt-[15vh]"
  data-command-palette
  role="presentation"
  onclick={onClose}
>
  <div
    class="w-full max-w-lg overflow-hidden rounded-lg border border-border bg-background shadow-md"
    role="presentation"
    onclick={(e) => e.stopPropagation()}
  >
    <Command.Root
      label="Command palette"
      vimBindings={false}
      onStateChange={(s) => {
        query = s.search;
      }}
    >
      <Command.Input
        autofocus
        placeholder="Type a command or person…"
        onkeydown={onPaletteFieldKey}
      />
      <Command.List>
        <Command.Viewport>
          <Command.Empty>No matching command.</Command.Empty>
          <Command.Group value="views">
            <Command.GroupHeading>Views</Command.GroupHeading>
            <Command.GroupItems>
              <Command.Item value="People" onSelect={() => onView("people")}>People</Command.Item>
              <Command.Item value="Search" onSelect={() => onView("search")}>Search</Command.Item>
              <Command.Item value="Review" onSelect={() => onView("review")}>Review</Command.Item>
              <Command.Item value="Import" onSelect={() => onView("import")}>Import</Command.Item>
              <Command.Item value="Doctor" onSelect={() => onView("doctor")}>Doctor</Command.Item>
            </Command.GroupItems>
          </Command.Group>
          <Command.Separator />
          <Command.Group value="people-list">
            <Command.GroupHeading>Jump to person</Command.GroupHeading>
            <Command.GroupItems>
              {#each palettePeople as p (p.id)}
                <Command.Item
                  value={`${personLabel(p)} ${p.id}`}
                  keywords={[personLabel(p), p.display_name]}
                  onSelect={() => onPerson(p)}
                >
                  {personLabel(p)}
                </Command.Item>
              {/each}
            </Command.GroupItems>
          </Command.Group>
        </Command.Viewport>
      </Command.List>
    </Command.Root>
  </div>
</div>
