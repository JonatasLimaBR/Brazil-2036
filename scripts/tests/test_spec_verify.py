from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import spec_verify  # noqa: E402


def _write(root: Path, rel: str, content: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # spec_verify resolves the repo root as parents[1] of its own file; point it at tmp
    monkeypatch.setattr(spec_verify, "__file__", str(tmp_path / "scripts" / "spec_verify.py"))
    (tmp_path / "scripts").mkdir()
    return tmp_path


def _run(repo: Path, doc: dict) -> int:
    path = repo / "check.yaml"
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")
    return spec_verify.run(path)


def test_files_exist_pass_and_fail(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(repo, "a.txt", "x")
    assert _run(repo, {"spec": "S", "checks": {"files_exist": ["a.txt"]}}) == 0
    assert _run(repo, {"spec": "S", "checks": {"files_exist": ["missing.txt"]}}) == 1
    assert "FAIL | file exists: missing.txt" in capsys.readouterr().out


def test_openapi_paths(repo: Path) -> None:
    _write(repo, "o.json", json.dumps({"paths": {"/v1/x": {}, "/v1/y": {}}}))
    ok = {"spec": "S", "checks": {"openapi_paths": {"file": "o.json", "paths": ["/v1/x"]}}}
    bad = {"spec": "S", "checks": {"openapi_paths": {"file": "o.json", "paths": ["/v1/z"]}}}
    assert _run(repo, ok) == 0
    assert _run(repo, bad) == 1


def _contract_doc(patterns: list[str]) -> dict:
    return {
        "spec": "S",
        "checks": {"contract_has_rules": {"file": "c.yaml", "patterns": patterns}},
    }


def test_contract_has_rules(repo: Path) -> None:
    _write(repo, "c.yaml", "min: 0\nevolution_policy: additive_only\n")
    assert _run(repo, _contract_doc([r"min:\s*0"])) == 0
    assert _run(repo, _contract_doc(["nope"])) == 1


def test_grep_absent(repo: Path) -> None:
    _write(repo, "src/main.ts", "const x = 1;\n")
    ok = {"spec": "S", "checks": {"grep_absent": [{"path": "src", "pattern": "SECRET"}]}}
    assert _run(repo, ok) == 0
    _write(repo, "src/bad.ts", "const SECRET = 1;\n")
    bad = {"spec": "S", "checks": {"grep_absent": [{"path": "src", "pattern": "SECRET"}]}}
    assert _run(repo, bad) == 1


def test_no_static_keys(repo: Path) -> None:
    _write(repo, "app/ok.py", "x = 1\n")
    assert _run(repo, {"spec": "S", "checks": {"no_static_keys": {"roots": ["app"]}}}) == 0
    _write(repo, "app/leak.json", '{"type": "service_account", "private_key": "x"}')
    assert _run(repo, {"spec": "S", "checks": {"no_static_keys": {"roots": ["app"]}}}) == 1


def test_gates_manifest_complete(repo: Path) -> None:
    manifest = {
        "gates": {
            "unit": {"status": "active"},
            "agent-eval": {"status": "n/a", "reason": "no agent yet"},
        }
    }
    _write(repo, ".github/ci/gates.yaml", yaml.safe_dump(manifest))
    cfg = {"file": ".github/ci/gates.yaml", "required_gates": ["unit", "agent-eval"]}
    assert _run(repo, {"spec": "S", "checks": {"gates_manifest_complete": cfg}}) == 0
    cfg_missing = {"file": ".github/ci/gates.yaml", "required_gates": ["unit", "security"]}
    assert _run(repo, {"spec": "S", "checks": {"gates_manifest_complete": cfg_missing}}) == 1


def test_agent_eval_without_reason_fails(repo: Path) -> None:
    manifest = yaml.safe_dump({"gates": {"agent-eval": {"status": "n/a"}}})
    _write(repo, ".github/ci/gates.yaml", manifest)
    cfg = {"file": ".github/ci/gates.yaml", "required_gates": ["agent-eval"]}
    assert _run(repo, {"spec": "S", "checks": {"gates_manifest_complete": cfg}}) == 1


def test_unknown_check_type_fails(repo: Path) -> None:
    assert _run(repo, {"spec": "S", "checks": {"bogus": []}}) == 1
