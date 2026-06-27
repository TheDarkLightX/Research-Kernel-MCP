from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from internal.research_kernel_mcp.kernel import ResearchKernel


def _run_with_claim(tmp_path: Path) -> tuple[ResearchKernel, str, str, str]:
    kernel = ResearchKernel(tmp_path)
    run = kernel.start_run(
        goal="Find safe weakening of a settlement invariant",
        title="settlement invariant weakening",
        domain="zenodex",
        success_criteria="SUPPORTED claims require evidence and refutation attempts.",
    )
    run_id = run["run"]["id"]
    dep = kernel.atom_add(
        run_id=run_id,
        atom_type="OBSERVATION",
        content="Settlement safety requires conservation and reject-is-no-op.",
        status="SUPPORTED",
        evidence_score=0.8,
    )["atom"]
    claim = kernel.atom_add(
        run_id=run_id,
        atom_type="CLAIM",
        content="Invariant X may be weakened if conservation remains explicit.",
        status="UNKNOWN",
        parent_ids=[dep["id"]],
        importance_score=0.9,
        uncertainty_score=0.8,
        refutability_score=0.9,
        tags=["settlement", "invariant"],
    )["atom"]
    return kernel, run_id, dep["id"], claim["id"]


def test_research_kernel_promotion_gate_fails_closed_then_supports(tmp_path: Path) -> None:
    kernel, run_id, _dep_id, claim_id = _run_with_claim(tmp_path)

    rejected = kernel.promote(
        claim_atom_id=claim_id,
        to_status="SUPPORTED",
        rationale="Trying before evidence should fail.",
    )
    assert rejected["ok"] is False
    assert set(rejected["gate"]["missing"]) >= {
        "has_support_evidence",
        "has_refutation_attempt",
        "has_provenance",
        "has_contradiction_search",
    }
    assert kernel.get_atom(claim_id)["status"] == "UNKNOWN"

    artifact = tmp_path / "proof.log"
    artifact.write_text("pytest replay passed\n", encoding="utf-8")
    evidence = kernel.evidence_attach(
        run_id=run_id,
        atom_id=claim_id,
        source_type="benchmark",
        source_uri="file://proof.log",
        summary="Focused replay passed.",
        reliability=0.9,
        artifact_path=str(artifact),
    )
    assert evidence["artifact"]["hash"].startswith("sha256:")
    assert Path(evidence["artifact"]["path"]).exists()
    assert evidence["promotion_readiness"]["has_provenance"] is True
    inline = kernel.evidence_attach(
        run_id=run_id,
        atom_id=claim_id,
        source_type="log",
        source_uri="inline://pytest-output",
        summary="Inline replay output.",
        artifact_text="pytest replay passed\n",
    )
    assert inline["artifact"]["hash"].startswith("sha256:")
    assert inline["promotion_readiness"]["has_provenance"] is True
    assert "inline://pytest-output" in kernel.get_atom(claim_id)["source_refs"]

    kernel.refute(
        run_id=run_id,
        target_atom_id=claim_id,
        strategy="Search for bounded traces that violate conservation.",
        tests=["generate rejecting settlement traces", "check conservation"],
    )
    kernel.evidence_attach(
        run_id=run_id,
        atom_id=claim_id,
        source_type="contradiction_search",
        source_uri="rk://memory/contradictions",
        summary="No prior contradiction found in the local kernel corpus.",
        reliability=0.7,
    )

    promoted = kernel.promote(
        claim_atom_id=claim_id,
        to_status="SUPPORTED",
        rationale="Evidence, refutation attempt, dependency, provenance, contradiction search, and replay are present.",
        checks={"replay_required": True, "replay_recipe": "pytest -q tests/core/test_settlement.py"},
    )
    assert promoted["ok"] is True
    assert promoted["gate"]["missing"] == []
    assert kernel.get_atom(claim_id)["status"] == "SUPPORTED"
    events = (tmp_path / "events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(events) >= 6
    assert any(json.loads(line)["event_type"] == "promotion_attempted" for line in events)


def test_refute_counterexample_text_requires_actual_flag(tmp_path: Path) -> None:
    kernel, run_id, _dep_id, claim_id = _run_with_claim(tmp_path)

    plan = kernel.refute(
        run_id=run_id,
        target_atom_id=claim_id,
        strategy="Try known CPSS-BC failures as adversarial context.",
        counterexample="Prior CPSS-BC witness, provided as context for the search plan.",
    )
    plan_atom = plan["refutation_atom"]
    assert plan["actual_counterexample"] is False
    assert plan_atom["type"] == "RISK"
    assert plan_atom["status"] == "UNDER_TEST"
    assert plan_atom["metadata"]["counterexample_context"].startswith("Prior CPSS-BC")
    assert plan["edge"]["edge_type"] == "TESTS"
    assert kernel.get_atom(claim_id)["status"] == "UNKNOWN"

    with pytest.raises(ValueError, match="counterexample is required"):
        kernel.refute(
            run_id=run_id,
            target_atom_id=claim_id,
            strategy="This is only actual if a witness is supplied.",
            counterexample_is_actual=True,
        )

    actual = kernel.refute(
        run_id=run_id,
        target_atom_id=claim_id,
        strategy="Construct a conservation-breaking trace.",
        counterexample="Trace T spends without a balancing debit.",
        counterexample_is_actual=True,
    )
    assert actual["actual_counterexample"] is True
    assert actual["refutation_atom"]["type"] == "COUNTEREXAMPLE"
    assert actual["edge"]["edge_type"] == "REFUTES"
    assert kernel.get_atom(claim_id)["status"] == "REFUTED"


def test_summary_only_evidence_reports_missing_provenance(tmp_path: Path) -> None:
    kernel, run_id, dep_id, claim_id = _run_with_claim(tmp_path)

    evidence = kernel.evidence_attach(
        run_id=run_id,
        atom_id=claim_id,
        source_type="support",
        summary="A useful note with no replayable source.",
        reliability=0.8,
    )
    assert evidence["promotion_readiness"]["has_provenance"] is False
    assert "source_uri" in evidence["promotion_readiness"]["hint"]

    kernel.refute(
        run_id=run_id,
        target_atom_id=claim_id,
        strategy="Search bounded traces for violations.",
        tests=["bounded trace generator"],
    )
    promoted = kernel.promote(
        claim_atom_id=claim_id,
        to_status="SUPPORTED",
        rationale="This should still fail because summary-only evidence has no provenance.",
        checks={"contradiction_search_done": True, "replay_recipe": "pytest -q tests/internal/test_research_kernel_mcp.py"},
    )
    assert promoted["ok"] is False
    assert "has_provenance" in promoted["gate"]["missing"]
    assert evidence["evidence"]["id"] in promoted["gate"]["diagnostics"]["evidence_without_provenance"]
    assert dep_id in kernel.get_atom(claim_id)["parent_ids"]


def test_retrieve_prior_failures_graph_neighbors_and_report(tmp_path: Path) -> None:
    kernel, run_id, _dep_id, claim_id = _run_with_claim(tmp_path)
    bad = kernel.refute(
        run_id=run_id,
        target_atom_id=claim_id,
        strategy="Construct a conservation-breaking trace.",
        counterexample="Trace T spends without a balancing debit.",
        counterexample_is_actual=True,
    )["refutation_atom"]
    assert kernel.get_atom(claim_id)["status"] == "REFUTED"
    kernel.evidence_attach(
        run_id=run_id,
        atom_id=bad["id"],
        source_type="counterexample",
        source_uri="generated://trace/T",
        summary="The trace violates the proposed weakening.",
        reliability=0.95,
    )

    prior = kernel.retrieve(run_id=run_id, modes=["prior_failures"], limit=5)
    assert any(item["atom"]["id"] == bad["id"] for item in prior["results"])

    neighbors = kernel.retrieve(
        run_id=run_id,
        atom_id=claim_id,
        modes=["graph_neighbors", "contradictory_evidence"],
        limit=10,
    )
    assert any(item["atom"]["id"] == bad["id"] for item in neighbors["results"])

    rejected = kernel.promote(
        claim_atom_id=claim_id,
        to_status="SUPPORTED",
        rationale="Refuted targets must stay blocked until superseded.",
        checks={"contradiction_search_done": True},
    )
    assert rejected["ok"] is False
    assert "has_no_refuting_evidence" in rejected["gate"]["missing"]

    report = kernel.report(run_id=run_id, include_graph=True)
    assert report["schema"] == "research_kernel/report/v1"
    assert report["summary"]["run"]["id"] == run_id
    assert report["contradictions"]
    assert report["graph"]["atoms"]
    assert "hidden chain-of-thought" in report["non_claims"][0]


def test_morph_score_frontier_and_lexical_retrieval(tmp_path: Path) -> None:
    kernel, run_id, _dep_id, claim_id = _run_with_claim(tmp_path)
    morph = kernel.morph(
        target="Invariant X can be weakened safely.",
        run_id=run_id,
        modes=["weaker_statement", "counterexample_search", "formal_spec"],
        store=True,
    )
    assert len(morph["reformulations"]) == 3
    assert len(morph["stored_atom_ids"]) == 3

    similar = kernel.retrieve(
        query="conservation explicit invariant weakened",
        run_id=run_id,
        modes=["similar_claims", "open_frontier_matches"],
        limit=10,
    )
    assert any(item["atom"]["id"] == claim_id for item in similar["results"])

    score = kernel.score_atom(claim_id)
    assert score["priority"] > 0
    frontier = kernel.frontier(run_id=run_id, limit=5)
    assert frontier["frontier"]
    assert frontier["frontier"][0]["next_action"]


def test_artifact_allowlist_rejects_outside_paths(tmp_path: Path) -> None:
    kernel, run_id, _dep_id, claim_id = _run_with_claim(tmp_path / "home")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside artifact\n", encoding="utf-8")
    with pytest.raises(ValueError, match="outside allowlist"):
        kernel.evidence_attach(
            run_id=run_id,
            atom_id=claim_id,
            source_type="benchmark",
            artifact_path=str(outside),
        )
    env_file = tmp_path / "home" / ".env"
    env_file.write_text("TOKEN=redacted\n", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing to ingest"):
        kernel.evidence_attach(
            run_id=run_id,
            atom_id=claim_id,
            source_type="benchmark",
            artifact_path=str(env_file),
        )


def test_server_self_test_runs_without_starting_stdio() -> None:
    proc = subprocess.run(
        [sys.executable, "internal/research_kernel_mcp/server.py", "--self-test"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["server"] == "research-kernel"
