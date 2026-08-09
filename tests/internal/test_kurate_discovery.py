from __future__ import annotations

from pathlib import Path

import pytest

from internal.research_kernel_mcp.kernel import ResearchKernel
from internal.research_kernel_mcp.kurate import (
    import_kurate_signal,
    kurate_verification_plan,
    list_kurate_candidates,
    normalise_kurate_snapshot,
)


def _snapshot() -> dict:
    return {
        "title": "A Frontier Paper",
        "identifier": "arXiv:2608.00001v1",
        "primary_uri": "https://arxiv.org/abs/2608.00001",
        "kurate_uri": "https://kurate.org/paper/example",
        "categories": ["cs.CR", "Public-key Cryptography"],
        "captured_at": "2026-08-09T22:00:00Z",
        "assessment_model": "example-model",
        "prompt_version": "kurate-16-metric",
        "assessment_summary": "Potentially important and unusually refutable.",
        "metrics": {
            "score": 8.0,
            "significance": 8.0,
            "rigor": 7.0,
            "novelty": 9.0,
            "clarity": 7.0,
            "difficulty": 8.0,
            "surprisingness": 8.0,
            "reproducibility": 6.0,
            "translational_potential": 5.0,
            "evidence_strength": 7.0,
            "generalisability": 7.0,
            "interdisciplinarity": 5.0,
            "refutation_value": 9.0,
            "replication_value": 7.0,
            "resource_intensity": 4.0,
            "foundationality": 8.0,
        },
        "reasons": {
            "novelty_reason": "Tests a new algebraic attack surface.",
            "refutation_value_reason": "A bounded counterexample would be decisive.",
        },
        "ranks": {"cs.CR": 12},
        "relevance_score": 0.95,
    }


def _run_with_claim(tmp_path: Path) -> tuple[ResearchKernel, str, str]:
    kernel = ResearchKernel(tmp_path)
    run = kernel.start_run(
        goal="Find and falsify frontier cryptography hypotheses",
        title="frontier cryptography",
        domain="cryptography",
        success_criteria="Primary-source evidence and refutation are required for support.",
    )
    run_id = run["run"]["id"]
    dependency = kernel.atom_add(
        run_id=run_id,
        atom_type="OBSERVATION",
        content="The target scheme uses an auxiliary isogeny sampler.",
        status="SUPPORTED",
    )["atom"]
    claim = kernel.atom_add(
        run_id=run_id,
        atom_type="CLAIM",
        content="The auxiliary sampler is context-independent.",
        status="UNKNOWN",
        parent_ids=[dependency["id"]],
        importance_score=0.9,
        uncertainty_score=0.9,
        refutability_score=0.9,
    )["atom"]
    return kernel, run_id, claim["id"]


def test_normalise_kurate_snapshot_is_discovery_only() -> None:
    signal = normalise_kurate_snapshot(_snapshot())
    assert signal["provider"] == "kurate"
    assert signal["signal_class"] == "discovery_only"
    assert signal["promotion_eligible"] is False
    assert signal["triage_score"] > 0.5
    assert signal["assessment_hash"].startswith("sha256:")
    assert signal["metrics"]["novelty"] == 9.0
    assert signal["limitations"]


def test_kurate_import_prioritises_candidate_without_supporting_target(tmp_path: Path) -> None:
    kernel, run_id, claim_id = _run_with_claim(tmp_path)

    imported = import_kurate_signal(
        kernel,
        run_id=run_id,
        snapshot=_snapshot(),
        target_atom_ids=[claim_id],
    )
    candidate = imported["candidate_atom"]
    assert candidate["type"] == "OBSERVATION"
    assert candidate["status"] == "CANDIDATE"
    assert candidate["evidence_score"] == 0.0
    assert candidate["metadata"]["kurate"]["promotion_eligible"] is False
    assert imported["promotion_boundary"]["eligible_as_claim_support"] is False
    assert imported["links"][0]["edge_type"] == "ANALOGIZES"

    evidence = imported["discovery_evidence"]["evidence"]
    assert evidence["source_type"] == "discovery_signal"
    assert evidence["source_uri"].startswith("https://kurate.org/")

    # The discovery signal may rank highly on the frontier...
    frontier = kernel.frontier(run_id=run_id, limit=20)
    assert any(item["atom_id"] == candidate["id"] for item in frontier["frontier"])

    # ...but it must not satisfy the target claim's scientific support gate.
    promoted = kernel.promote(
        claim_atom_id=claim_id,
        to_status="SUPPORTED",
        rationale="Kurate alone must never make this claim supported.",
        checks={"contradiction_search_done": True},
    )
    assert promoted["ok"] is False
    assert "has_support_evidence" in promoted["gate"]["missing"]
    assert kernel.get_atom(claim_id)["status"] == "UNKNOWN"


def test_kurate_candidates_and_verification_plan(tmp_path: Path) -> None:
    kernel, run_id, claim_id = _run_with_claim(tmp_path)
    imported = import_kurate_signal(
        kernel,
        run_id=run_id,
        snapshot=_snapshot(),
        target_atom_ids=[claim_id],
    )
    candidate_id = imported["candidate_atom"]["id"]

    candidates = list_kurate_candidates(
        kernel,
        run_id=run_id,
        minimum_triage_score=0.5,
        target_atom_id=claim_id,
    )
    assert [item["atom_id"] for item in candidates["candidates"]] == [candidate_id]
    assert candidates["candidates"][0]["next_action"].startswith("independently retrieve")

    plan = kurate_verification_plan(kernel, candidate_id)
    assert plan["primary_uri"].startswith("https://arxiv.org/")
    assert [step["id"] for step in plan["steps"]] == [
        "identity",
        "primary_read",
        "claim_extract",
        "independent_assessment",
        "evidence_attach",
        "contradiction_search",
    ]
    assert any("does not establish academic novelty" in item for item in plan["non_claims"])


def test_kurate_snapshot_validation() -> None:
    bad = _snapshot()
    bad["kurate_uri"] = "https://example.com/not-kurate"
    with pytest.raises(ValueError, match="kurate.org"):
        normalise_kurate_snapshot(bad)

    bad = _snapshot()
    bad["metrics"]["novelty"] = 11
    with pytest.raises(ValueError, match="between 1 and 10"):
        normalise_kurate_snapshot(bad)
