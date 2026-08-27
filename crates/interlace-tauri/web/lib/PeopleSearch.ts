import { tick } from "svelte";

export async function whenSearchPaneReady(
  setView: (v: "search") => void,
  isBusy: () => boolean,
): Promise<HTMLInputElement | null> {
  setView("search");
  for (let i = 0; i < 40; i++) {
    await tick();
    if (isBusy()) continue;
    const qEl = document.getElementById("q");
    if (qEl instanceof HTMLInputElement) return qEl;
  }
  const qEl = document.getElementById("q");
  return qEl instanceof HTMLInputElement ? qEl : null;
}

export function submitChromeSearch(
  e: Event,
  ready: () => Promise<HTMLInputElement | null>,
) {
  e.preventDefault();
  void ready().then((qEl) => {
    if (!qEl) return;
    qEl.focus();
    qEl.form?.requestSubmit();
  });
}
