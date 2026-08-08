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

  let peopleCache = [];
  let selectedId = null;
  let timeline = [];
  let tlIndex = 0;
  let includeGroups = false;

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
    refreshPeople();
    refreshEvents();
  }

  function renderPeople() {
    const q = ($("person-filter").value || "").trim().toLowerCase();
    const ul = $("people");
    ul.innerHTML = "";
    for (const p of peopleCache) {
      const label = (p.display_name || "") + (p.is_self ? " self" : "");
      if (q && !label.toLowerCase().includes(q)) continue;
      const li = document.createElement("li");
      li.textContent = p.is_self ? `${p.display_name} (self)` : p.display_name;
      li.dataset.id = String(p.id);
      if (p.is_self) li.classList.add("self");
      if (p.id === selectedId) li.classList.add("active");
      li.addEventListener("click", () => selectPerson(p.id));
      ul.append(li);
    }
  }

  async function refreshPeople() {
    peopleCache = await invoke("people");
    renderPeople();
  }

  async function refreshEvents() {
    const ev = await invoke("link_events");
    const ul = $("events");
    ul.innerHTML = "";
    for (const e of ev) {
      const li = document.createElement("li");
      const lab = document.createElement("span");
      lab.textContent = `#${e.id} ${e.op}`;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "secondary";
      btn.textContent = "undo";
      btn.addEventListener("click", async () => {
        if (!confirm(`Undo event ${e.id} (${e.op})?`)) return;
        try {
          await invoke("person_undo_cmd", { eventId: e.id });
          await refreshPeople();
          await refreshEvents();
          if (selectedId) await selectPerson(selectedId);
        } catch (err) {
          showErr(err);
        }
      });
      li.append(lab, btn);
      ul.append(li);
    }
  }

  function renderTimeline() {
    const ol = $("timeline");
    ol.innerHTML = "";
    timeline.forEach((row, i) => {
      const li = document.createElement("li");
      if (i === tlIndex) li.classList.add("active");
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = [
        row.sent_at || "no date",
        row.platform,
        row.conversation_kind,
        row.from_me ? "you" : "them",
        row.conversation_title || "",
      ]
        .filter(Boolean)
        .join(" · ");
      const body = document.createElement("p");
      body.className = "body";
      body.textContent = row.body_text || row.subject || "";
      li.append(meta, body);
      li.addEventListener("click", () => {
        tlIndex = i;
        renderTimeline();
      });
      ol.append(li);
    });
    $("btn-more").hidden = timeline.length === 0;
  }

  async function selectPerson(id, append) {
    selectedId = id;
    renderPeople();
    const show = await invoke("person_show", { id });
    $("person-title").textContent = show.display_name || `person ${id}`;
    const idents = $("idents");
    idents.innerHTML = "";
    for (const ident of show.identities || []) {
      const li = document.createElement("li");
      const lab = document.createElement("span");
      lab.textContent = `${ident.platform} ${ident.kind} ${ident.display_name || ident.value}`;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "secondary";
      btn.textContent = "unlink";
      btn.addEventListener("click", async () => {
        if (!confirm(`Unlink identity ${ident.id}?`)) return;
        try {
          await invoke("person_unlink_cmd", { identityId: ident.id });
          await selectPerson(id);
          await refreshEvents();
        } catch (err) {
          showErr(err);
        }
      });
      li.append(lab, btn);
      idents.append(li);
    }
    const before = append && timeline.length ? timeline[timeline.length - 1].sent_at : null;
    const rows = await invoke("person_timeline", {
      id,
      includeGroups,
      limit: 80,
      before,
    });
    timeline = append ? timeline.concat(rows) : rows;
    tlIndex = 0;
    renderTimeline();
    $("timeline").focus();
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
  $("person-filter").addEventListener("input", renderPeople);
  $("include-groups").addEventListener("change", async (e) => {
    includeGroups = !!e.target.checked;
    if (selectedId) await selectPerson(selectedId);
  });
  $("btn-more").addEventListener("click", async () => {
    if (selectedId) await selectPerson(selectedId, true);
  });
  $("btn-merge").addEventListener("click", async () => {
    if (!selectedId) {
      showErr("select a person first");
      return;
    }
    const other = Number($("merge-into").value);
    if (!other) {
      showErr("enter the other person id");
      return;
    }
    if (!confirm(`Merge ${selectedId} and ${other}?`)) return;
    try {
      const out = await invoke("person_merge_cmd", {
        a: selectedId,
        b: other,
        keep: selectedId,
      });
      await refreshPeople();
      await refreshEvents();
      await selectPerson(out.survivor);
    } catch (e) {
      showErr(e);
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.target && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA")) {
      if (e.key === "Escape") e.target.blur();
      return;
    }
    if (e.key === "/") {
      e.preventDefault();
      $("person-filter").focus();
      return;
    }
    if (e.key === "j" || e.key === "ArrowDown") {
      if (!timeline.length) return;
      tlIndex = Math.min(timeline.length - 1, tlIndex + 1);
      renderTimeline();
      e.preventDefault();
    }
    if (e.key === "k" || e.key === "ArrowUp") {
      if (!timeline.length) return;
      tlIndex = Math.max(0, tlIndex - 1);
      renderTimeline();
      e.preventDefault();
    }
  });

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
