"""#279 / #300 lock: G1–G3 / G5 for the tauri_gate split. Line count is not a gate."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

from common import fail, repo_root, run

from tauri_gate.split_prefixes import (
    _SPLIT_219_FOLD_TOKENS,
    _SPLIT_MAIN_ASSERTS,
    _SPLIT_PROTECTED_PREFIXES,
)

_SPLIT_ENTRY_CMD = "python3 pipeline/tools/gate_tauri.py"
_SPLIT_AREA_MIN = 8
_SPLIT_SELF = "assert_gate_tauri_split"
_SPLIT_PKG = "tauri_gate"
_SPLIT_PROTECTED_HOMES = ("review.py", "contrast.py", "import_doctor.py", "motion.py")
# scan.py public surface. Parse walkers may stay private. One-assert keep-checks leave.
_SPLIT_SCAN_READERS = (
    "_web_sources",
    "_web_logic",
    "_timeline_block",
    "_css_var",
    "_chrome_en_text",
)
_SPLIT_SCAN_KEEP_OUT = (
    "_PRETTY_WHATSAPP",
    "_CHROME_SEARCH_HOOK",
    "_A11Y_ROLE_LISTBOX",
    "_STATUS_CELEBRATION",
)
_SPLIT_EXISTING_TOOL_ASSERTS = {
    "assert_blind.py",
    "assert_matrix_not_ignored.py",
    "assert_no_crate.py",
    "assert_no_test_edits.py",
    "assert_no_todo.py",
}

_SPLIT_BOOTSTRAP_NEEDLES = (
    "publish = false",
    "tauri-plugin-http",
    "tauri-plugin-updater",
    "CSP",
    "Interlace.entitlements",
    "signingIdentity",
    "network.server",
    "network.client",
    "allow-jit",
    "assert_app_notarize",
    '["npm", "ci"]',
    '["npm", "run", "build"]',
    '"clippy"',
    '"deny"',
    '"reqwest"',
    '"hyper"',
)
def _split_yaml_job(wf: str, name: str) -> str:
    m = re.search(rf"(?m)^  {re.escape(name)}:\n", wf)
    if not m:
        return ""
    rest = wf[m.end() :]
    nxt = re.search(r"(?m)^  [A-Za-z0-9_-]+:\n", rest)
    return wf[m.start() : m.end() + (nxt.start() if nxt else len(rest))]


def _split_job_run_lines(job: str) -> list[str]:
    lines: list[str] = []
    for m in re.finditer(r"(?m)^[ \t]+run:[ \t]*(.*)$", job):
        val = m.group(1).strip()
        if val in {"|", ">"}:
            continue
        if val:
            lines.append(val)
    return lines


def _split_const_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _split_fold_str(node: ast.AST) -> str | None:
    direct = _split_const_str(node)
    if direct is not None:
        return direct
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _split_fold_str(node.left)
        right = _split_fold_str(node.right)
        if left is not None and right is not None:
            return left + right
        return left if left is not None else right
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            chunk = _split_const_str(value)
            if chunk is None:
                break
            parts.append(chunk)
        return "".join(parts) if parts else None
    return None


def _split_fail_prefixes(fn_src: str) -> list[str]:
    try:
        tree = ast.parse(fn_src)
    except SyntaxError:
        return []
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Name) or func.id != "fail" or not node.args:
            continue
        folded = _split_fold_str(node.args[0])
        if folded and folded not in out:
            out.append(folded)
    return out


def _split_fn_sources(paths: list[Path]) -> dict[str, str]:
    found: dict[str, str] = {}
    for path in paths:
        src = path.read_text()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            seg = ast.get_source_segment(src, node)
            if not seg:
                continue
            if node.name in found:
                found[node.name] = found[node.name] + "\n" + seg
            else:
                found[node.name] = seg
    return found


def _split_main_calls(main_src: str) -> list[str]:
    try:
        tree = ast.parse(main_src)
    except SyntaxError:
        return []
    fn = next(
        (
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "main"
        ),
        None,
    )
    if fn is None:
        return []
    names: list[str] = []
    for stmt in fn.body:
        if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
            continue
        func = stmt.value.func
        if isinstance(func, ast.Name) and func.id.startswith("assert_"):
            names.append(func.id)
    return names


def _split_gate_paths() -> tuple[Path, Path, Path]:
    root = repo_root()
    tools = root / "pipeline" / "tools"
    return root, tools / "gate_tauri.py", tools / _SPLIT_PKG


def assert_gate_tauri_split(crate: Path) -> None:
    """#279 / #300: split assert_* into tauri_gate/; entry + CI command unchanged.

    G1 CI one-liner. G2 main() call order + bootstrap. G3 #128 / #219–#222
    fail prefixes (and the #219 keep-check #278 folded). G5 package + size
    (no file ≥ 1_200) + scan surface + docs. G4 is the existing full gate
    (do not re-run npm/clippy here).
    """
    root, entry, pkg = _split_gate_paths()
    if not entry.is_file():
        fail("#279: G5 — pipeline/tools/gate_tauri.py must stay the entry")
    entry_src = entry.read_text()
    try:
        entry_tree = ast.parse(entry_src)
    except SyntaxError as exc:
        fail(f"#279: G5 — pipeline/tools/gate_tauri.py must parse: {exc}")

    # G1 — CI tauri job is still exactly the one-liner.
    ci = root / ".github" / "workflows" / "ci.yml"
    if not ci.is_file():
        fail("#279: G1 — .github/workflows/ci.yml required")
    wf = ci.read_text()
    if "python3 -m tauri_gate" in wf:
        fail("#279: G1 — no python3 -m tauri_gate")
    job = _split_yaml_job(wf, "tauri")
    if not job:
        fail("#279: G1 — ci.yml tauri job required")
    gate_runs = [
        line
        for line in _split_job_run_lines(job)
        if "gate_tauri" in line or "tauri_gate" in line
    ]
    if gate_runs != [_SPLIT_ENTRY_CMD]:
        fail(
            "#279: G1 — ci.yml tauri job step must stay exactly "
            f"`{_SPLIT_ENTRY_CMD}`"
        )
    for m in re.finditer(r"(?m)^  ([A-Za-z0-9_-]+):\n", wf):
        other = m.group(1)
        if other == "tauri":
            continue
        block = _split_yaml_job(wf, other)
        if "gate_tauri.py" in block or "tauri_gate" in block:
            fail("#279: G1 — no new CI job for the tauri gate")

    # G2 — same main() assert_* calls (order) + bootstrap.
    main_node = next(
        (
            n
            for n in entry_tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "main"
        ),
        None,
    )
    if main_node is None:
        fail("#279: G2 — gate_tauri.py main() required")
    main_src = ast.get_source_segment(entry_src, main_node) or ""
    calls = [n for n in _split_main_calls(main_src) if n != _SPLIT_SELF]
    frozen = list(_SPLIT_MAIN_ASSERTS)
    idx = 0
    for name in calls:
        if idx < len(frozen) and name == frozen[idx]:
            idx += 1
    if idx != len(frozen):
        missing = [n for n in frozen if n not in calls]
        if missing:
            fail(
                "#279: G2 — main() must still call "
                + ", ".join(missing)
                + " (same order as master; a missing call is a softened gate)"
            )
        expected = frozen[idx]
        prev = frozen[idx - 1] if idx else "(start)"
        fail(
            f"#279: G2 — main() assert_* order drifted: expected {expected} "
            f"after {prev}"
        )
    for needle in _SPLIT_BOOTSTRAP_NEEDLES:
        if needle not in main_src:
            fail(f"#279: G2 — main() bootstrap must still include {needle!r}")

    scan_paths = [entry]
    if pkg.is_dir():
        scan_paths.extend(sorted(p for p in pkg.glob("*.py") if p.is_file()))
    fn_sources = _split_fn_sources(scan_paths)
    for name in frozen:
        if name == "assert_app_notarize":
            continue
        if name not in fn_sources:
            fail(
                f"#279: G2 — {name} must still exist "
                "(moved body, not dropped)"
            )

    # G3 — protected fail prefixes still live on the five functions.
    for name, prefixes in _SPLIT_PROTECTED_PREFIXES.items():
        body = fn_sources.get(name, "")
        if not body:
            fail(
                f"#279: G3 — {name} required "
                "(move #128 / #219–#222; do not drop)"
            )
        messages = _split_fail_prefixes(body)
        for prefix in prefixes:
            if not any(msg == prefix or msg.startswith(prefix) for msg in messages):
                fail(
                    f"#279: G3 — {name} must keep fail prefix {prefix!r} "
                    "(move, do not rewrite)"
                )
    status_src = fn_sources.get("assert_status_tokens", "")
    for token in _SPLIT_219_FOLD_TOKENS:
        if token not in status_src:
            fail(
                "#279: G3 — assert_status_tokens must keep #219/#278 token "
                f"{token!r}"
            )

    # G5 — package + size + entry + docs. G4 is the rest of this script.
    clash = entry.parent / "gate_tauri"
    if clash.is_dir():
        fail(
            "#279: G5 — do not name the package gate_tauri "
            "(clash with the entry script)"
        )
    if not pkg.is_dir():
        fail(f"#279: G5 — package pipeline/tools/{_SPLIT_PKG}/ is missing")

    if not (pkg / "__init__.py").is_file():
        fail("#279: G5 — pipeline/tools/tauri_gate/__init__.py required")
    if not (pkg / "scan.py").is_file():
        fail(
            "#279: G5 — pipeline/tools/tauri_gate/scan.py required "
            "(shared readers + one _tag_name)"
        )
    missing_homes = [n for n in _SPLIT_PROTECTED_HOMES if not (pkg / n).is_file()]
    if missing_homes:
        fail(
            "#279: G5 — review.py / tokens.py / import_doctor.py required "
            "(homes for #128 / #219 / #220 / #221 / #222)"
        )
    area_py = [
        p
        for p in pkg.glob("*.py")
        if p.is_file() and p.name not in {"__init__.py", "scan.py"}
    ]
    if len(area_py) < _SPLIT_AREA_MIN:
        fail(
            "#279: G5 — ~8–10 area modules required under tauri_gate/ "
            "(not one file per assert_*)"
        )
    one_each = [p for p in area_py if p.name.startswith("assert_")]
    if len(one_each) >= 20:
        fail("#279: G5 — do not split one file per assert_* (approach B)")
    tools = entry.parent
    chrome_files = {
        f"{name}.py"
        for name in frozen
        if name != "assert_app_notarize"
    }
    flat = [
        p.name
        for p in tools.glob("assert_*.py")
        if p.is_file()
        and p.name in chrome_files
        and p.name not in _SPLIT_EXISTING_TOOL_ASSERTS
    ]
    if flat:
        fail(
            "#279: G5 — do not add flat pipeline/tools/assert_*.py "
            "siblings (approach C)"
        )

    # #300 — scan.py public surface: five readers + one _tag_name + CSP.
    # Parse walkers may stay private. One-assert keep-checks must leave.
    scan_src = (pkg / "scan.py").read_text()
    try:
        scan_tree = ast.parse(scan_src)
    except SyntaxError as exc:
        fail(f"#300: G5 — pipeline/tools/tauri_gate/scan.py must parse: {exc}")
    scan_fns = [
        n.name for n in scan_tree.body if isinstance(n, ast.FunctionDef)
    ]
    for reader in _SPLIT_SCAN_READERS:
        if reader not in scan_fns:
            fail(
                f"#300: G5 — scan.py must define {reader} "
                "(shared reader; do not drop)"
            )
    tag_defs = scan_fns.count("_tag_name")
    if tag_defs != 1:
        fail(
            f"#300: G5 — scan.py must define exactly one _tag_name "
            f"(found {tag_defs})"
        )
    scan_binds: set[str] = set()
    for node in scan_tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    scan_binds.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(
            node.target, ast.Name
        ):
            scan_binds.add(node.target.id)
    if "CSP" not in scan_binds:
        fail(
            "#300: G5 — scan.py must keep CSP next to the readers (do not copy)"
        )
    leftover = [n for n in _SPLIT_SCAN_KEEP_OUT if n in scan_binds]
    if leftover:
        fail(
            "#300: G5 — scan.py must not define one-assert keep-check "
            + ", ".join(leftover)
            + " (move next to the owning assert; do not copy)"
        )

    doc = ast.get_docstring(entry_tree) or ""
    if "def main(" not in entry_src or not doc:
        fail(
            "#279: G5 — gate_tauri.py must stay the entry "
            "(module docstring + def main)"
        )

    pipe_docs = root / "docs" / "hacking" / "pipeline.md"
    tauri_docs = root / "docs" / "hacking" / "tauri.md"
    for label, path in (("pipeline.md", pipe_docs), ("tauri.md", tauri_docs)):
        text = path.read_text() if path.is_file() else ""
        if _SPLIT_ENTRY_CMD not in text:
            fail(
                f"#279: G5 — docs/hacking/{label} must keep "
                f"`{_SPLIT_ENTRY_CMD}`"
            )
    named = ""
    if pipe_docs.is_file():
        named += pipe_docs.read_text()
    if tauri_docs.is_file():
        named += "\n" + tauri_docs.read_text()
    if "tauri_gate" not in named:
        fail(
            "#279: G5 — docs/hacking/pipeline.md and/or docs/hacking/tauri.md "
            "must name the tauri_gate package"
        )

    compile_paths = [entry, *sorted(p for p in pkg.glob("*.py") if p.is_file())]
    compiled = run(
        [sys.executable, "-m", "py_compile", *[str(p) for p in compile_paths]],
        check=False,
    )
    if compiled.returncode != 0:
        fail(
            "#279: G5 — py_compile failed:\n"
            + (compiled.stderr or compiled.stdout or "")
        )
