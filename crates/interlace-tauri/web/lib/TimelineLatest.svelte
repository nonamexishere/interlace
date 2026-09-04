<script lang="ts">
  import { fade } from "svelte/transition";
  import { Button } from "$lib/components/ui/button/index.js";
  import { chromeMotionMs } from "./motion";
  import { t } from "$lib/i18n";

  let { onclick }: { onclick: () => void } = $props();
</script>

<div class="absolute end-3 bottom-3 z-10" transition:fade={{ duration: chromeMotionMs() }}>
  <Button variant="secondary" size="sm" class="shadow-sm" aria-label={t("latest")} {onclick}>
    {t("latest")}
  </Button>
</div>
