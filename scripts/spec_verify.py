from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import yaml

Row = tuple[str, bool, str]
CheckFn = Callable[[Any, Path], list[Row]]

_CHECKS: dict[str, CheckFn] = {}

_KEY_SHAPES = (
    re.compile(r'"type"\s*:\s*"service_account"'),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r'"private_key"\s*:\s*"-----BEGIN'),
)
_PRUNE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "dist",
    "build",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "__pycache__",
    "tests",
}
_MAX_BYTES = 512_000


def _check(name: str) -> Callable[[CheckFn], CheckFn]:
    def deco(fn: CheckFn) -> CheckFn:
        _CHECKS[name] = fn
        return fn

    return deco


@_check("files_exist")
def _files_exist(items: list[str], root: Path) -> list[Row]:
    return [(f"file exists: {p}", (root / p).is_file(), "") for p in items]


@_check("openapi_paths")
def _openapi_paths(cfg: dict[str, Any], root: Path) -> list[Row]:
    target = root / cfg["file"]
    if not target.is_file():
        return [(f"openapi file {cfg['file']}", False, "missing")]
    have = set(json.loads(target.read_text(encoding="utf-8")).get("paths", {}))
    return [(f"openapi path: {p}", p in have, "") for p in cfg["paths"]]


@_check("contract_has_rules")
def _contract_has_rules(cfg: dict[str, Any], root: Path) -> list[Row]:
    target = root / cfg["file"]
    text = target.read_text(encoding="utf-8") if target.is_file() else ""
    return [
        (f"contract matches /{rx}/", re.search(rx, text) is not None, "") for rx in cfg["patterns"]
    ]


@_check("grep_absent")
def _grep_absent(items: list[dict[str, str]], root: Path) -> list[Row]:
    rows: list[Row] = []
    for entry in items:
        base = root / entry["path"]
        pattern = entry["pattern"]
        hits = [
            str(p.relative_to(root))
            for p in _iter_files(base)
            if pattern in p.read_text(encoding="utf-8", errors="ignore")
        ]
        rows.append((f"absent {pattern!r} under {entry['path']}", not hits, "; ".join(hits)))
    return rows


@_check("no_static_keys")
def _no_static_keys(cfg: dict[str, Any], root: Path) -> list[Row]:
    hits: list[str] = []
    for base_name in cfg["roots"]:
        for path in _iter_files(root / base_name):
            if path.stat().st_size > _MAX_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(shape.search(text) for shape in _KEY_SHAPES):
                hits.append(str(path.relative_to(root)))
    return [("no static credential shapes in repo", not hits, "; ".join(hits))]


@_check("gates_manifest_complete")
def _gates_manifest_complete(cfg: dict[str, Any], root: Path) -> list[Row]:
    target = root / cfg["file"]
    if not target.is_file():
        return [(f"gates manifest {cfg['file']}", False, "missing")]
    manifest = yaml.safe_load(target.read_text(encoding="utf-8")).get("gates", {})
    rows: list[Row] = []
    for gate in cfg["required_gates"]:
        entry = manifest.get(gate, {})
        status = entry.get("status")
        ok = status == "active" or (status == "n/a" and bool(entry.get("reason")))
        detail = "" if ok else f"status={status!r} reason={entry.get('reason')!r}"
        rows.append((f"SPEC-031 gate declared: {gate}", ok, detail))
    return rows


def _iter_files(base: Path) -> Iterable[Path]:
    if base.is_file():
        yield base
        return
    if not base.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in _PRUNE_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def run(spec_check_path: str | Path) -> int:
    root = Path(__file__).resolve().parents[1]
    doc = yaml.safe_load(Path(spec_check_path).read_text(encoding="utf-8"))
    spec = doc["spec"]

    rows: list[Row] = []
    for kind, arg in doc["checks"].items():
        if kind not in _CHECKS:
            rows.append((f"unknown check type: {kind}", False, ""))
            continue
        rows.extend(_CHECKS[kind](arg, root))

    ok = True
    for label, passed, detail in rows:
        marker = "PASS" if passed else "FAIL"
        suffix = f" -- {detail}" if detail and not passed else ""
        print(f"{marker} | {label}{suffix}")
        ok = ok and passed

    print(f"\n{spec} spec-verify: {'PASS' if ok else 'FAIL'} ({len(rows)} checks)")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: spec_verify.py <spec-checks/SPEC-XXX.yaml>", file=sys.stderr)
        return 2
    return run(argv[1])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
