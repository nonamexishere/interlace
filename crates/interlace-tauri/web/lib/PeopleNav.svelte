<script lang="ts">
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { t } from "$lib/i18n";
  import type { Density } from "./PeoplePrefs";
  import type { Status } from "./api";

  let {
    view = $bindable<"people" | "search" | "review" | "import" | "doctor">("people"),
    searchQ = $bindable(""),
    density,
    st,
    doctorCount,
    booting,
    opening,
    persistDensity,
    onSearchSubmit,
  }: {
    view?: "people" | "search" | "review" | "import" | "doctor";
    searchQ?: string;
    density: Density;
    st: Status;
    doctorCount: number;
    booting: boolean;
    opening: boolean;
    persistDensity: (next: Density) => void;
    onSearchSubmit: (e: Event) => void;
  } = $props();
</script>

<nav class="flex flex-wrap items-center gap-1 border-b border-border px-3 py-1 text-sm">
  <Button size="sm" variant={view === "people" ? "default" : "ghost"} onclick={() => (view = "people")}
    >{t("people")}</Button
  >
  <Button size="sm" variant={view === "search" ? "default" : "ghost"} onclick={() => (view = "search")}
    >{t("search")}</Button
  >
  <Button size="sm" variant={view === "review" ? "default" : "ghost"} onclick={() => (view = "review")}
    >{t("review")}{#if st.review_open} ({st.review_open}){/if}</Button
  >
  <Button size="sm" variant={view === "import" ? "default" : "ghost"} onclick={() => (view = "import")}
    >{t("import")}</Button
  >
  <Button size="sm" variant={view === "doctor" ? "default" : "ghost"} onclick={() => (view = "doctor")}
    >{t("doctor")}{#if doctorCount} ({doctorCount}){/if}</Button
  >
  <form class="ml-auto min-w-[10rem] max-w-[16rem] flex-1" data-chrome-search onsubmit={onSearchSubmit}>
    <Input
      type="search"
      bind:value={searchQ}
      placeholder={t("searchPlaceholder")}
      aria-label={t("search")}
      autocomplete="off"
      class="h-8"
      disabled={booting || opening}
    />
  </form>
  <Button
    variant="ghost"
    size="sm"
    class="h-8 shrink-0"
    data-density-toggle
    aria-pressed={density === "comfortable"}
    aria-label={density === "comfortable" ? "Comfortable density" : "Default density"}
    onclick={() => persistDensity(density === "comfortable" ? "default" : "comfortable")}
  >
    {density === "comfortable" ? "Comfortable" : "Default"}
  </Button>
</nav>
