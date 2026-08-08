/* global window */
(function () {
  const invoke = (...args) => {
    const core = window.__TAURI__ && window.__TAURI__.core;
    if (!core || !core.invoke) {
      throw new Error("Tauri bridge missing");
    }
    return core.invoke(...args);
  };

  const $ = (id) => document.getElementById(id);
  const errEl = $("err");
  const setup = $("setup");
  const session = $("session");

  function showErr(msg) {
    if (!msg) {
      errEl.hidden = true;
      errEl.textContent = "";
      return;
    }
    errEl.hidden = false;
    errEl.textContent = String(msg);
  }

  function csv(s) {
    return String(s || "")
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);
  }

  function renderStatus(st) {
    setup.hidden = true;
    session.hidden = false;
    $("path").textContent = st.path || "";
    const counts = $("counts");
    counts.innerHTML = "";
    const rows = [
      ["owner", st.owner_display_name || "—"],
      ["phone region", st.default_phone_region || "—"],
      ["messages", st.messages],
      ["identities", st.identities],
      ["persons", st.persons_live],
      ["review open", st.review_open],
    ];
    for (const [k, v] of rows) {
      const dt = document.createElement("dt");
      dt.textContent = k;
      const dd = document.createElement("dd");
      dd.textContent = v == null ? "—" : String(v);
      counts.append(dt, dd);
    }
    const li = st.last_import;
    $("last").textContent = li
      ? `last import id=${li.id} status=${li.status}`
      : "no imports yet";
    const ul = $("warns");
    ul.innerHTML = "";
    for (const w of st.warnings || []) {
      const item = document.createElement("li");
      item.textContent = w;
      ul.append(item);
    }
  }

  async function openPath(path) {
    showErr("");
    const st = await invoke("open", { path });
    renderStatus(st);
  }

  $("btn-create").addEventListener("click", async () => {
    showErr("");
    const region = $("region").value.trim();
    if (!region) {
      showErr("phone-region is required (e.g. TR, US)");
      return;
    }
    try {
      const folder = await invoke("pick_folder");
      if (!folder) return;
      const name = $("name").value.trim();
      const st = await invoke("init", {
        path: folder,
        phoneRegion: region,
        name: name || null,
        emails: csv($("emails").value),
        phones: csv($("phones").value),
      });
      renderStatus(st);
    } catch (e) {
      showErr(e);
    }
  });

  async function openPicker() {
    showErr("");
    try {
      const folder = await invoke("pick_folder");
      if (!folder) return;
      await openPath(folder);
    } catch (e) {
      showErr(e);
    }
  }

  $("btn-open").addEventListener("click", openPicker);
  $("btn-other").addEventListener("click", openPicker);

  (async () => {
    try {
      const remembered = await invoke("remembered_path");
      if (remembered) {
        await openPath(remembered);
        return;
      }
    } catch (e) {
      showErr(e);
    }
    setup.hidden = false;
  })();
})();
