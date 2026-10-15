from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_runner():
    path = Path(__file__).resolve().parents[2] / "examples" / "aira_v2" / "run_research_kernel.py"
    spec = importlib.util.spec_from_file_location("aira_v2_runner", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_aira_v2_research_run_uses_fail_closed_kernel(tmp_path: Path) -> None:
    module = _load_runner()
    home = tmp_path / "research"
    result = module.run(home)
    assert result["run_id"] == "zrm-aira-v2-frontier-20260714"
    summary = result["summary"]
    assert summary["counts_by_type"]["HYPOTHESIS"] >= 16
    assert summary["counts_by_status"]["TESTABLE"] >= 16
    assert summary["counts_by_status"]["SUPPORTED"] >= 1
    report = json.loads((home / "research_kernel_report.json").read_text(encoding="utf-8"))
    supported = [item for item in report["supported_claims"] if item["type"] == "CLAIM"]
    assert any(item["id"] == "aira_claim_provenance_not_output" for item in supported)
    graph = json.loads((home / "research_graph.json").read_text(encoding="utf-8"))
    assert graph["atoms"]
    assert graph["edges"]
    assert (home / "research_kernel.sqlite3").is_file()
    assert (home / "events.jsonl").is_file()


def test_seed_has_unique_sources_and_hypotheses() -> None:
    module = _load_runner()
    seed = module.load_seed()
    source_ids = [item["id"] for item in seed["sources"]]
    hypothesis_ids = [item["id"] for item in seed["hypotheses"]]
    assert len(source_ids) == len(set(source_ids))
    assert len(hypothesis_ids) == len(set(hypothesis_ids))
    assert len(source_ids) >= 20
    assert len(hypothesis_ids) >= 16
