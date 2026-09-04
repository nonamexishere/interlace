<script lang="ts">
  import type { Snippet } from "svelte";
  import { fade } from "svelte/transition";
  import { Button } from "$lib/components/ui/button/index.js";
  import { chromeMotionMs } from "./motion";
  import { t } from "$lib/i18n";

  let { onclick, children }: { onclick: () => void; children: Snippet } = $props();
</script>

<div class="absolute end-3 bottom-3 z-10" transition:fade={{ duration: chromeMotionMs() }}>
  <Button variant="secondary" size="sm" class="shadow-sm" aria-label={t("latest")} {onclick}>
    {@render children()}
  </Button>
</div>
