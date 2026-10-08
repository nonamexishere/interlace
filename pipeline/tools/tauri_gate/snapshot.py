"""#430 — Doctor lists local snapshots and can take or restore one.

Take has no confirm. Restore uses the one existing ConfirmDialog.
Copy archive to… stays. There is no `fn backup` and no filesystem path.
"""

from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan_parse_rest import _ts_function_body
from tauri_gate.scan_rust_rest import _rust_function_body
from tauri_gate.voice_transcript import _mount_path, _text, _uses_t

_EXACT = {
    "en": {
        "snapshots": "Snapshots",
        "snapshotTake": "Take snapshot",
        "snapshotRestore": "Restore",
        "snapshotRestoreTitle": "Restore this snapshot?",
        "snapshotRestoreBody": (
            "Replaces the open archive with this snapshot. "
            "Messages added after it are removed."
        ),
        "snapshotSaved": "Snapshot saved.",
        "snapshotRestored": "Archive restored.",
        "snapshotRestoreFailed": "This snapshot was not restored.",
    },
    "tr": {
        "snapshots": "Anlık görüntüler",
        "snapshotTake": "Anlık görüntü al",
        "snapshotRestore": "Geri yükle",
        "snapshotRestoreTitle": "Bu anlık görüntüye dönülsün mü?",
        "snapshotRestoreBody": (
            "Açık arşivi bu anlık görüntüyle değiştirir. "
            "Sonradan eklenen iletiler silinir."
        ),
        "snapshotSaved": "Anlık görüntü kaydedildi.",
        "snapshotRestored": "Arşiv geri yüklendi.",
        "snapshotRestoreFailed": "Bu anlık görüntü geri yüklenmedi.",
    },
}

_CONTROLS = (
    ("data-snapshot-list", "snapshots"),
    ("data-snapshot-take", "snapshotTake"),
    ("data-snapshot-restore", "snapshotRestore"),
)


def _element(src: str, marker: str) -> str:
    at = src.find(marker)
    if at < 0:
        return ""
    start = src.rfind("<", 0, at)
    if start < 0:
        start = at
    close = src.find("</", at)
    if close < 0:
        close = min(len(src), at + 500)
    return src[start:close]


def _onclick_body(doctor: str, marker: str) -> str:
    el = _element(doctor, marker)
    m = re.search(r"onclick=\{([A-Za-z_][A-Za-z0-9_]*)\}", el)
    if not m:
        # Per-row restore: onclick={() => askSnapshot(id)}
        m = re.search(
            r"onclick=\{\s*\(\)\s*=>\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(",
            el,
        )
    if not m:
        return el
    return _ts_function_body(doctor, m.group(1)) or el


def _assigns_archive_slot_none(body: str) -> bool:
    """True when the archive slot is assigned None, not merely mentioned."""
    if re.search(r"\barchive\b[^;\n]{0,240}=\s*None\b", body):
        return True
    names = re.findall(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*[^;\n]*\barchive\s*\.\s*lock\s*\(",
        body,
    )
    for name in names:
        if re.search(
            rf"(?<![\w])(?:\*\s*)?{re.escape(name)}\s*=\s*None\b",
            body,
        ):
            return True
    return False


def _fns_calling(ipc: str, needle: str) -> list[str]:
    names = re.findall(
        r"(?:pub(?:\(crate\))?\s+)?(?:async\s+)?fn\s+([A-Za-z0-9_]+)",
        ipc,
    )
    return [name for name in names if needle in _rust_function_body(ipc, name)]


def _locale_bits(crate: Path) -> list[str]:
    bits: list[str] = []
    for lang, filename in (("en", "en.ts"), ("tr", "tr.ts")):
        entries = _chrome_pack_entries(_text(crate / "web" / "lib" / "locales" / filename))
        for key, exact in _EXACT[lang].items():
            got = entries.get(key)
            if got is None:
                bits.append(f"{filename} lacks {key}")
            elif got != exact:
                bits.append(f"{filename} {key} is not the exact string")
    return bits


def assert_snapshot(crate: Path) -> None:
    """#430: Doctor snapshot list, take, and restore. Missing controls fail closed."""
    doctor = _text(crate / "web" / "lib" / "DoctorPane.svelte")
    if "data-copy-archive" not in doctor or 't("noSeparateBackup")' not in doctor:
        fail("snapshot: Backup section lost Copy archive to…")
        return
    missing = [marker for marker, _key in _CONTROLS if marker not in doctor]
    if missing:
        fail("snapshot controls are missing")
        return

    bits: list[str] = []
    for marker, key in _CONTROLS:
        if not _uses_t(_element(doctor, marker), key):
            bits.append(f'{marker} does not use t("{key}")')
    mount = _mount_path(doctor)
    for name in ("snapshot_archive", "restore_snapshot", "list_snapshots"):
        if name in mount:
            bits.append(f"Doctor onMount calls {name}")
    if len(re.findall(r"<ConfirmDialog\b", doctor)) != 1:
        bits.append("ConfirmDialog is not exactly one")
    if not re.search(r"onconfirm\s*=\s*\{\s*runPending\s*\}", doctor):
        bits.append("onconfirm is not {runPending}")
    pending = _ts_function_body(doctor, "runPending")
    if "gcCas:" not in pending:
        bits.append("runPending lacks gcCas:")
    take_body = _onclick_body(doctor, "data-snapshot-take")
    if "confirmOpen" in take_body or "ConfirmDialog" in take_body:
        bits.append("data-snapshot-take confirms")
    restore_body = _onclick_body(doctor, "data-snapshot-restore")
    if "confirmOpen" not in restore_body and "snapshotRestoreTitle" not in restore_body:
        bits.append("data-snapshot-restore does not use the confirm dialog")
    for marker in ("data-snapshot-take", "data-snapshot-restore"):
        window = _element(doctor, marker) + _onclick_body(doctor, marker)
        if "copy_archive_to" in window or "PathBuf" in window or "dialog" in window:
            bits.append(f"{marker} invokes copy_archive_to or a filesystem path")
    if "restore_snapshot_at" in doctor:
        bits.append("Doctor calls restore_snapshot_at")
    ipc = _text(crate / "src" / "ipc.rs")
    if re.search(r"\bfn backup\b", ipc):
        bits.append("ipc.rs has fn backup")
    for needle in ("snapshot_archive(", "restore_snapshot("):
        owners = _fns_calling(ipc, needle)
        if not owners:
            bits.append(f"ipc.rs does not call {needle}")
            continue
        for name in owners:
            body = _rust_function_body(ipc, name)
            if "import running" not in body:
                bits.append(f"{name} does not refuse import running")
    load_body = _ts_function_body(doctor, "load")
    snap_at = load_body.find("snapshotList")
    if snap_at < 0:
        bits.append("Doctor load does not call snapshotList")
    else:
        after = load_body[snap_at + len("snapshotList") :]
        stop = after.find("scanning = false")
        if stop < 0:
            bits.append("Doctor load has no scanning = false after snapshotList")
        elif "scanGen" not in after[:stop]:
            bits.append(
                "Doctor load does not check scanGen after snapshotList "
                "and before scanning = false"
            )
    take_fn = _rust_function_body(ipc, "snapshot_take")
    restore_fn = _rust_function_body(ipc, "snapshot_restore")
    for name, body in (("snapshot_take", take_fn), ("snapshot_restore", restore_fn)):
        if "import running" not in body:
            bits.append(f"{name} does not refuse import running")
        if "copy in progress" not in body:
            bits.append(f"{name} does not refuse copy in progress")
    if "disabled={busy" not in _element(doctor, "data-copy-archive"):
        bits.append("data-copy-archive lacks disabled={busy")
    if "archive_on_file" not in restore_fn or "None" not in restore_fn:
        bits.append("snapshot_restore body lacks archive_on_file and None")
    if _assigns_archive_slot_none(restore_fn) and (
        "archive_root" not in restore_fn or "rebuild_menu" not in restore_fn
    ):
        bits.append(
            "snapshot_restore assigns the archive slot None without archive_root and rebuild_menu"
        )
    bits.extend(_locale_bits(crate))
    if bits:
        fail("snapshot: " + "; ".join(bits))
