from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from internal.research_kernel_mcp.kurate import (
    import_kurate_signal,
    kurate_verification_plan,
    list_kurate_candidates,
    normalise_kurate_snapshot,
)
from internal.research_kernel_mcp.kernel import ResearchKernel


def _snapshot(
    *,
    title: str = "A Paper",
    relevance: float = 0.9,
    rigor: float = 8.0,
):
    return {
        "title": title,
        "identifier": "arXiv:2601.00001",
        "primary_uri": "https://arxiv.org/abs/2601.00001",
        "kurate_uri": "https://kurate.org/paper/example-id",
        "categories": ["cs.CR", "math.NT"],
        "captured_at": "2026-08-09T00:00:00Z",
        "assessment_model": "Claude Opus 4.8",
        "prompt_version": "https://kurate.org/prompts",
        "assessment_summary": (
            "Potentially relevant structural cryptography result."
        ),
        "metrics": {
            "score": 7.5,
            "significance": 7.0,
            "rigor": rigor,
            "novelty": 8.5,
            "evidence_strength": 7.0,
            "refutation_value": 8.0,
            "replication_value": 2.0,
            "foundationality": 8.0,
            "surprisingness": 7.5,
            "reproducibility": 6.0,
            "interdisciplinarity": 5.0,
        },
        "reasons": {
            "rigor": (
                "The paper states explicit hypotheses and machine-checkable "
                "proof obligations."
            ),
            "novelty": "It proposes a new source-to-mathematics refinement.",
        },
        "ranks": {"category_rank": 12, "category_size": 900},
        "relevance_score": relevance,
        "metadata": {"capture_method": "manual_public_page_snapshot"},
    }


def _run_with_claim(tmp_path: Path):
    kernel = ResearchKernel(tmp_path)
    run = kernel.start_run(goal="Map the isogeny cryptography frontier")
    run_id = run["run"]["id"]
    dependency = kernel.atom_add(
        run_id=run_id,
        atom_type="OBSERVATION",
        content=(
            "The production verifier has a source-bound semantic obligation."
        ),
        status="SUPPORTED",
    )["atom"]
    claim = kernel.atom_add(
        run_id=run_id,
        atom_type="CLAIM",
        content="The source-bound semantic obligation is complete.",
        status="UNKNOWN",
        parent_ids=[dependency["id"]],
    )["atom"]
    return kernel, run_id, claim["id"]


def test_normalise_kurate_snapshot_is_deterministic_and_discovery_only() -> None:
    left = normalise_kurate_snapshot(_snapshot())
    right = normalise_kurate_snapshot(_snapshot())
    assert left == right
    assert left["provider"] == "kurate"
    assert left["signal_class"] == "discovery_only"
    assert left["promotion_eligible"] is False
    assert 0.0 <= left["triage_score"] <= 1.0
    assert left["assessment_hash"].startswith("sha256:")
    assert "peer review" in left["limitations"][0]


def test_import_creates_candidate_not_claim_evidence(tmp_path: Path) -> None:
    kernel, run_id, claim_id = _run_with_claim(tmp_path)
    imported = import_kurate_signal(
        kernel,
        run_id=run_id,
        snapshot=_snapshot(),
        target_atom_ids=[claim_id],
        atom_id="kurate-paper-1",
    )

    candidate = imported["candidate_atom"]
    assert candidate["id"] == "kurate-paper-1"
    assert candidate["type"] == "OBSERVATION"
    assert candidate["status"] == "CANDIDATE"
    assert candidate["evidence_score"] == 0.0
    assert {
        "kurate",
        "discovery_signal",
        "literature_candidate",
    }.issubset(candidate["tags"])
    assert candidate["metadata"]["kurate"]["promotion_eligible"] is False
    assert (
        imported["discovery_evidence"]["evidence"]["source_type"]
        == "discovery_signal"
    )
    assert imported["links"][0]["edge_type"] == "ANALOGIZES"
    assert kernel.get_atom(claim_id)["status"] == "UNKNOWN"

    with kernel._connect() as conn:
        target_evidence = conn.execute(
            "SELECT COUNT(*) FROM evidence WHERE atom_id = ?",
            (claim_id,),
        ).fetchone()[0]
    assert target_evidence == 0


def test_candidate_listing_sorts_by_triage_and_can_filter_by_target(
    tmp_path: Path,
) -> None:
    kernel, run_id, claim_id = _run_with_claim(tmp_path)
    import_kurate_signal(
        kernel,
        run_id=run_id,
        snapshot=_snapshot(title="Lower", relevance=0.2, rigor=5.0),
        target_atom_ids=[claim_id],
        atom_id="lower",
    )
    import_kurate_signal(
        kernel,
        run_id=run_id,
        snapshot=_snapshot(title="Higher", relevance=1.0, rigor=9.5),
        target_atom_ids=[claim_id],
        atom_id="higher",
    )

    listed = list_kurate_candidates(
        kernel,
        run_id=run_id,
        target_atom_id=claim_id,
        limit=10,
    )
    assert [
        item["atom_id"] for item in listed["candidates"]
    ] == ["higher", "lower"]
    assert listed["candidates"][0]["next_action"].startswith(
        "independently retrieve"
    )


def test_kurate_link_does_not_satisfy_claim_promotion_provenance(
    tmp_path: Path,
) -> None:
    kernel, run_id, claim_id = _run_with_claim(tmp_path)
    import_kurate_signal(
        kernel,
        run_id=run_id,
        snapshot=_snapshot(),
        target_atom_ids=[claim_id],
    )
    kernel.evidence_attach(
        run_id=run_id,
        atom_id=claim_id,
        source_type="support",
        summary="Unproven support note without a primary source.",
    )
    kernel.refute(
        run_id=run_id,
        target_atom_id=claim_id,
        strategy="Search for a source-level counterexample.",
    )

    rejected = kernel.promote(
        claim_atom_id=claim_id,
        to_status="SUPPORTED",
        rationale="Kurate discovery must not supply provenance.",
        checks={
            "contradiction_search_done": True,
            "replay_recipe": "pytest",
        },
    )
    assert rejected["ok"] is False
    assert "has_provenance" in rejected["gate"]["missing"]


def test_verification_plan_from_import(tmp_path: Path) -> None:
    kernel, run_id, _claim_id = _run_with_claim(tmp_path)
    imported = import_kurate_signal(
        kernel,
        run_id=run_id,
        snapshot=_snapshot(),
    )
    plan = kurate_verification_plan(
        kernel,
        imported["candidate_atom"]["id"],
    )
    assert plan["primary_uri"].startswith("https://arxiv.org/")
    assert [step["id"] for step in plan["steps"]] == [
        "identity",
        "primary_read",
        "claim_extract",
        "independent_assessment",
        "evidence_attach",
        "contradiction_search",
    ]
    assert "does not establish academic novelty" in plan["non_claims"][0]


def test_invalid_snapshot_fields_fail_closed() -> None:
    invalid = _snapshot()
    invalid["metrics"]["rigor"] = 11
    with pytest.raises(ValueError, match="between 1 and 10"):
        normalise_kurate_snapshot(invalid)

    invalid = _snapshot()
    invalid["primary_uri"] = ""
    with pytest.raises(ValueError, match="primary_uri is required"):
        normalise_kurate_snapshot(invalid)

    invalid = _snapshot()
    invalid["metrics"]["made_up_metric"] = 8
    with pytest.raises(ValueError, match="unknown Kurate metrics"):
        normalise_kurate_snapshot(invalid)


def test_kurate_extension_self_test_runs() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "internal/research_kernel_mcp/kurate_server.py",
            "--self-test",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["kurate_extension"] is True
    assert "rk_kurate_import" in payload["kurate_tools"]
