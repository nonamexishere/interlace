import { listen } from "@tauri-apps/api/event";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { api } from "./api";
import { LAST_PERSON_PREF, LAST_VIEW_PREF } from "./PeoplePrefs";

export type PeopleBootCtx = {
  openPicker: () => Promise<void>;
  setView: (v: "people" | "search" | "review" | "import" | "doctor") => void;
  importDroppedPaths: (paths: string[]) => Promise<void>;
  openPath: (path: string) => Promise<void>;
  showErr: (e: unknown) => void;
  setSetup: (v: boolean) => void;
  setBooting: (v: boolean) => void;
  err: string;
};

export function startPeopleBoot(ctx: PeopleBootCtx): () => void {
  let menuGone = false;
  const menuUnlisten: Array<() => void> = [];
  const keepMenu = (unlisten: () => void) => {
    if (menuGone) unlisten();
    else menuUnlisten.push(unlisten);
  };
  void listen("menu-open-archive", ctx.openPicker).then(keepMenu);
  void listen("menu-open-recent", (e) => {
    const path = e.payload;
    if (typeof path === "string" && path.length > 0) {
      void ctx.openPath(path).catch(ctx.showErr);
    }
  }).then(keepMenu);
  void listen("menu-import", () => {
    ctx.setView("import");
  }).then(keepMenu);
  void listen("menu-view", (e) => {
    const next = e.payload;
    if (next === "people") ctx.setView("people");
    else if (next === "search") ctx.setView("search");
    else if (next === "review") ctx.setView("review");
    else if (next === "doctor") ctx.setView("doctor");
  }).then(keepMenu);
  void listen("menu-switch-archive", () => {
    void switchToSetup(ctx);
  }).then(keepMenu);
  void getCurrentWebview()
    .onDragDropEvent((event) => {
      if (event.payload.type !== "drop") return;
      void ctx.importDroppedPaths(event.payload.paths ?? []);
    })
    .then(keepMenu);
  void (async () => {
    try {
      const remembered = await api.rememberedPath();
      if (remembered) {
        await ctx.openPath(remembered);
        return;
      }
    } catch (e) {
      ctx.showErr(e);
      ctx.setSetup(true);
    } finally {
      ctx.setBooting(false);
    }
    ctx.setSetup(true);
  })();
  return () => {
    menuGone = true;
    for (const unlisten of menuUnlisten) unlisten();
  };
}

async function switchToSetup(ctx: PeopleBootCtx) {
  try {
    await api.closeArchive();
  } catch {
    return;
  }
  ctx.err = "";
  ctx.setSetup(true);
  localStorage.removeItem(LAST_VIEW_PREF);
  localStorage.removeItem(LAST_PERSON_PREF);
}
