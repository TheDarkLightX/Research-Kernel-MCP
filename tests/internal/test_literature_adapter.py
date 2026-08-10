from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from internal.research_kernel_mcp.kernel import ResearchKernel
from internal.research_kernel_mcp.literature import (
    LiteratureAdapterError,
    normalize_literature_export,
)


def _citracer_export() -> bytes:
    return json.dumps(
        {
            "metadata": {
                "retrieval_policy": {"kind": "lawful_open_access_only"},
            },
            "nodes": [
                {
                    "id": "doi:10.1234/root",
                    "title": "Root paper",
                    "authors": ["A. Author"],
                    "year": 2025,
                    "doi": "10.1234/root",
                    "status": "root",
                    "depth": 0,
                    "keyword_hits": ["projection operator"],
                },
                {
                    "id": "arxiv:2608.00001v2",
                    "title": "Cited paper",
                    "authors": ["B. Author"],
                    "year": 2026,
                    "arxiv_id": "2608.00001v2",
                    "status": "analyzed",
                    "depth": 1,
                    "keyword_hits": [],
                },
            ],
            "edges": [
                {
                    "source": "doi:10.1234/root",
                    "target": "arxiv:2608.00001v2",
                    "type": "primary",
                    "depth": 1,
                    "context": "Root cites the result.",
                }
            ],
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _mosaic_export() -> bytes:
    return json.dumps(
        {
            "status": "ok",
            "query": "projection operator",
            "count": 1,
            "papers": [
                {
                    "uid": "doi:10.5678/example",
                    "title": "A MOSAIC result",
                    "authors": ["C. Author"],
                    "year": 2024,
                    "doi": "https://doi.org/10.5678/Example",
                    "source": "OpenAlex",
                    "is_open_access": True,
                    "relevance_score": 0.8125,
                }
            ],
            "errors": ["One optional source timed out"],
        },
        separators=(",", ":"),
    ).encode("utf-8")


def test_citracer_normalization_preserves_graph_and_policy() -> None:
    batch = normalize_literature_export(_citracer_export(), provider="citracer")

    assert batch.provider == "citracer"
    assert len(batch.candidates) == 2
    assert len(batch.relations) == 1
    root = batch.candidates[0]
    assert root["authority"] == "triage_only"
    assert root["paper"]["doi"] == "10.1234/root"
    assert root["context"]["is_new"] is None
    assert root["provenance"]["retrieval_policy_kind"] == "lawful_open_access_only"
    relation = batch.relations[0]
    assert relation["source_work_key"] == "doi:10.1234/root"
    assert relation["target_work_key"] == "arxiv:2608.00001"


def test_mosaic_normalization_preserves_partial_failure_as_warning() -> None:
    batch = normalize_literature_export(_mosaic_export(), provider="mosaic")

    assert len(batch.candidates) == 1
    assert batch.candidates[0]["paper"]["doi"] == "10.5678/example"
    assert batch.candidates[0]["context"]["relevance_decimal"] == "0.8125"
    assert batch.warnings == ("One optional source timed out",)


def test_shared_candidate_contract_matches_popperpad_golden_digest() -> None:
    raw = json.dumps(
        {
            "status": "ok",
            "query": "projection",
            "count": 1,
            "papers": [{
                "uid": "doi:10.1234/x",
                "title": "Shared fixture",
                "authors": ["A"],
                "year": 2026,
                "doi": "10.1234/X",
                "source": "OpenAlex",
                "is_open_access": True,
                "relevance_score": 0.75,
            }],
            "errors": [],
        },
        separators=(",", ":"),
    ).encode()
    candidate = normalize_literature_export(raw, provider="mosaic").candidates[0]
    semantic = json.dumps(
        candidate,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    assert hashlib.sha256(semantic).hexdigest() == (
        "98eb90f01d292968f95ffb6228d14544312bdcbaa3fa1ea57e279425da26a0af"
    )


def test_duplicate_keys_and_dangling_edges_are_quarantined() -> None:
    with pytest.raises(LiteratureAdapterError, match="duplicate JSON key"):
        normalize_literature_export(
            b'{"nodes":[],"nodes":[],"edges":[]}',
            provider="citracer",
        )

    payload = json.loads(_citracer_export())
    payload["edges"][0]["target"] = "doi:10.9999/missing"
    with pytest.raises(LiteratureAdapterError, match="unknown node"):
        normalize_literature_export(
            json.dumps(payload).encode("utf-8"),
            provider="citracer",
        )


def test_kernel_import_is_triage_only_and_records_citation_and_warning(tmp_path: Path) -> None:
    kernel = ResearchKernel(tmp_path)
    run_id = kernel.start_run(goal="Test literature import", run_id="literature-test")["run"]["id"]

    citracer_path = tmp_path / "citracer.json"
    citracer_path.write_bytes(_citracer_export())
    result = kernel.import_literature_file(
        run_id=run_id,
        provider="citracer",
        artifact_path=citracer_path,
    )
    assert result["ok"] is True
    assert len(result["candidates"]) == 2
    assert len(result["relations"]) == 1
    edge = kernel.get_edge(result["relations"][0]["edge_id"])
    assert edge["edge_type"] == "CITES"

    candidate_id = result["candidates"][0]["atom_id"]
    atom = kernel.get_atom(candidate_id)
    assert atom["status"] == "CANDIDATE"
    assert atom["evidence_score"] == 0.0
    assert atom["metadata"]["authority"] == "triage_only"
    blocked = kernel.promote(
        claim_atom_id=candidate_id,
        to_status="SUPPORTED",
        rationale="Discovery must not promote.",
        checks={"contradiction_search_done": True},
    )
    assert blocked["ok"] is False
    assert "has_claim_authority" in blocked["gate"]["missing"]

    mosaic_path = tmp_path / "mosaic.json"
    mosaic_path.write_bytes(_mosaic_export())
    mosaic = kernel.import_literature_file(
        run_id=run_id,
        provider="mosaic",
        artifact_path=mosaic_path,
    )
    assert len(mosaic["warning_atom_ids"]) == 1
    warning = kernel.get_atom(mosaic["warning_atom_ids"][0])
    assert warning["status"] == "UNKNOWN"
    assert "negative-knowledge" in warning["tags"]
