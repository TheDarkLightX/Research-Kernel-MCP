from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from internal.research_kernel_mcp.kernel import ResearchKernel
from internal.research_kernel_mcp.kurate import (
    KURATE_METRICS,
    KurateAdapterError,
    fetch_kurate_candidates,
    normalize_kurate_response,
)


def _row(*, score: float = 8.5, novelty: float | None = 7.5) -> dict[str, Any]:
    return {
        "paper_id": "6404916f-e61d-4fb7-bc59-eb518ab326e5",
        "title": "A bounded discovery result",
        "category": "cs.AI",
        "categories": ["cs.AI", "cs.LG"],
        "authors": ["Ada Researcher"],
        "published": "2026-08-09T00:00:00Z",
        "arxiv_id": "2608.01234v1",
        "ratings": {
            "score": score,
            "significance": 8,
            "rigor": 9,
            "novelty": novelty,
            "clarity": 8.5,
        },
    }


def _raw(row: dict[str, Any] | None = None) -> bytes:
    payload = {
        "dataset": "live",
        "total": 1,
        "timing_ms": 3.14159,
        "rows": [_row() if row is None else row],
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _query(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "search": "bounded",
        "categories": ["cs.AI"],
        "date_range": "30d",
        "sort_key": "novelty",
        "sort_dir": "desc",
        "limit": 10,
        "offset": 0,
    }
    value.update(overrides)
    return value


class _Response:
    status = 200

    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def read(self, _limit: int) -> bytes:
        return self.payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def _contains_float(value: Any) -> bool:
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(_contains_float(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_float(child) for child in value)
    return False


def test_fetch_builds_bounded_uri_and_integer_scaled_candidate() -> None:
    seen: dict[str, Any] = {}

    def opener(request: Any, *, timeout: int) -> _Response:
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["accept"] = request.headers["Accept"]
        return _Response(_raw())

    batch = fetch_kurate_candidates(
        search="projection operator",
        categories=["math.AG", "cs.AI"],
        date_range="30d",
        sort_key="novelty",
        sort_dir="desc",
        limit=5,
        offset=2,
        timeout_seconds=7,
        opener=opener,
    )

    assert seen["timeout"] == 7
    assert seen["accept"] == "application/json"
    assert "search=projection+operator" in seen["url"]
    assert "cats=cs.AI%2Cmath.AG" in seen["url"]
    assert len(batch.candidates) == 1
    candidate = batch.candidates[0]
    assert candidate["authority"] == "triage_only"
    assert candidate["paper"]["arxiv_id_base"] == "2608.01234"
    assert candidate["assessment"]["metrics_milli"]["score"] == 8500
    assert candidate["assessment"]["metrics_milli"]["novelty"] == 7500
    assert set(candidate["assessment"]["metrics_milli"]) == set(KURATE_METRICS)
    assert candidate["assessment"]["metrics_milli"]["refutation_value"] is None
    assert candidate["selection"]["position"] == 2
    assert not _contains_float(candidate)
    assert batch.snapshot_ref.startswith("sha256:")
    assert batch.raw_response_ref.startswith("sha256:")


def test_shared_candidate_contract_matches_popperpad_golden_digest() -> None:
    row = {
        "paper_id": "p-1",
        "title": "Shared fixture",
        "category": "math.LO",
        "categories": ["math.LO"],
        "authors": ["A"],
        "published": "2026-08-09",
        "arxiv_id": "2608.00001v2",
        "ratings": {"score": 8.125, "novelty": None},
    }
    candidate = normalize_kurate_response(
        json.dumps({"dataset": "live", "total": 1, "rows": [row]}, separators=(",", ":")).encode(),
        request_uri=(
            "https://kurate.org/api/papers-list?dataset=live&sort_key=score&sort_dir=desc"
            "&offset=0&limit=1&include_categories=false&include_histograms=false"
        ),
        query=_query(
            search="",
            categories=[],
            date_range="all",
            sort_key="score",
            limit=1,
        ),
    ).candidates[0]
    semantic_bytes = json.dumps(
        candidate,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    assert hashlib.sha256(semantic_bytes).hexdigest() == (
        "c05efe9b6a9bf8a8782d398051b3bf321d88e249df5a140e0a7fce1df2c8b896"
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        ({"limit": 41}, "limit"),
        ({"sort_key": "unknown"}, "sort_key"),
        ({"categories": ["cs.AI&admin=true"]}, "category"),
        ({"timeout_seconds": 0}, "timeout_seconds"),
    ),
)
def test_request_validation_fails_before_network(kwargs: dict[str, Any], message: str) -> None:
    def opener(*_args: object, **_kwargs: object) -> _Response:
        raise AssertionError("network must not be reached")

    with pytest.raises(KurateAdapterError, match=message):
        fetch_kurate_candidates(opener=opener, **kwargs)


def test_schema_drift_duplicate_keys_and_bad_metrics_are_quarantined() -> None:
    duplicate = b'{"rows":[],"rows":[],"dataset":"live","total":0}'
    with pytest.raises(KurateAdapterError, match="duplicate JSON key"):
        normalize_kurate_response(
            duplicate,
            request_uri="https://kurate.org/api/papers-list?limit=1",
            query=_query(limit=1),
        )

    unknown = _row()
    unknown["ratings"]["future_metric"] = 8
    with pytest.raises(KurateAdapterError, match="unknown rating fields"):
        normalize_kurate_response(
            _raw(unknown),
            request_uri="https://kurate.org/api/papers-list?limit=10",
            query=_query(),
        )

    invalid = _row(score=11)
    with pytest.raises(KurateAdapterError, match="between 0 and 10"):
        normalize_kurate_response(
            _raw(invalid),
            request_uri="https://kurate.org/api/papers-list?limit=10",
            query=_query(),
        )


def test_kernel_import_is_idempotent_and_cannot_supply_promotion_evidence(tmp_path: Path) -> None:
    kernel = ResearchKernel(tmp_path)
    run_id = kernel.start_run(goal="Test Kurate discovery authority", run_id="kurate-test")["run"]["id"]
    batch = normalize_kurate_response(
        _raw(),
        request_uri="https://kurate.org/api/papers-list?limit=10",
        query=_query(),
    )

    first = kernel.import_kurate_batch(run_id=run_id, batch=batch, apply_triage_scores=True)
    second = kernel.import_kurate_batch(run_id=run_id, batch=batch, apply_triage_scores=True)
    assert first["ok"] is True
    assert first["candidates"][0]["created"] is True
    assert second["candidates"][0]["created"] is False
    atom_id = first["candidates"][0]["atom_id"]
    atom = kernel.get_atom(atom_id)
    assert atom["status"] == "CANDIDATE"
    assert atom["evidence_score"] == 0.0
    assert atom["uncertainty_score"] == 1.0
    assert atom["metadata"]["authority"] == "triage_only"
    assert atom["novelty_score"] == 0.75

    blocked = kernel.promote(
        claim_atom_id=atom_id,
        to_status="SUPPORTED",
        rationale="Discovery alone must never promote.",
        checks={"contradiction_search_done": True, "replay_recipe": "none"},
    )
    assert blocked["ok"] is False
    assert "has_claim_authority" in blocked["gate"]["missing"]
    assert "has_support_evidence" in blocked["gate"]["missing"]


def test_new_snapshot_supersedes_prior_discovery_receipt(tmp_path: Path) -> None:
    kernel = ResearchKernel(tmp_path)
    run_id = kernel.start_run(goal="Track Kurate score changes", run_id="kurate-supersede")["run"]["id"]
    old_batch = normalize_kurate_response(
        _raw(_row(score=7.5)),
        request_uri="https://kurate.org/api/papers-list?limit=10",
        query=_query(),
    )
    new_batch = normalize_kurate_response(
        _raw(_row(score=9.0)),
        request_uri="https://kurate.org/api/papers-list?limit=10",
        query=_query(),
    )
    old = kernel.import_kurate_batch(run_id=run_id, batch=old_batch)["candidates"][0]
    new = kernel.import_kurate_batch(run_id=run_id, batch=new_batch)["candidates"][0]

    assert old["atom_id"] != new["atom_id"]
    assert kernel.get_atom(old["atom_id"])["status"] == "SUPERSEDED"
    assert kernel.get_atom(new["atom_id"])["status"] == "CANDIDATE"


def test_discovery_failure_is_retained_as_unknown_negative_knowledge(tmp_path: Path) -> None:
    kernel = ResearchKernel(tmp_path)
    run_id = kernel.start_run(goal="Retain discovery failures", run_id="kurate-failure")["run"]["id"]
    result = kernel.record_discovery_failure(
        run_id=run_id,
        provider="kurate",
        query=_query(),
        error_code="REMOTE_UNAVAILABLE",
        detail="Kurate could not be reached",
    )
    assert result["ok"] is False
    atom = kernel.get_atom(result["failure_atom_id"])
    assert atom["status"] == "UNKNOWN"
    assert "negative-knowledge" in atom["tags"]
    assert atom["metadata"]["does_not_support_claims"] is True
