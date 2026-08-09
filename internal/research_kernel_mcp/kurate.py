from __future__ import annotations

from typing import Any

from internal.research_kernel_mcp.kernel import ResearchKernel, canonical_json, clamp_score, sha256_ref


KURATE_METRICS = (
    "score",
    "significance",
    "rigor",
    "novelty",
    "clarity",
    "difficulty",
    "surprisingness",
    "reproducibility",
    "translational_potential",
    "evidence_strength",
    "generalisability",
    "interdisciplinarity",
    "refutation_value",
    "replication_value",
    "resource_intensity",
    "foundationality",
)

# Research-triage weights, not a scientific-quality theorem. The profile favors
# work that is rigorous, potentially refuting, evidentially strong, and reusable.
DEFAULT_TRIAGE_WEIGHTS = {
    "rigor": 0.18,
    "novelty": 0.14,
    "evidence_strength": 0.14,
    "refutation_value": 0.12,
    "replication_value": 0.08,
    "foundationality": 0.12,
    "significance": 0.10,
    "surprisingness": 0.05,
    "reproducibility": 0.04,
    "interdisciplinarity": 0.03,
}

DISCOVERY_SOURCE_TYPE = "discovery_signal"
DISCOVERY_TAGS = ("discovery_signal", "kurate", "literature_candidate")


def _nonempty(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is required")
    return text


def _normalise_metrics(raw: Any) -> dict[str, float | None]:
    if not isinstance(raw, dict):
        raise ValueError("metrics must be a JSON object")
    unknown = sorted(set(raw) - set(KURATE_METRICS))
    if unknown:
        raise ValueError(f"unknown Kurate metrics: {unknown}")
    metrics: dict[str, float | None] = {}
    observed = 0
    for name in KURATE_METRICS:
        value = raw.get(name)
        if value is None:
            metrics[name] = None
            continue
        number = float(value)
        if not 1.0 <= number <= 10.0:
            raise ValueError(f"metric {name} must be between 1 and 10 or null")
        metrics[name] = number
        observed += 1
    if observed == 0:
        raise ValueError("at least one Kurate metric is required")
    return metrics


def _normalise_reasons(raw: Any) -> dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("reasons must be a JSON object")
    reasons: dict[str, str] = {}
    for key, value in raw.items():
        name = str(key).removesuffix("_reason")
        if name not in KURATE_METRICS:
            raise ValueError(f"unknown Kurate reason field: {key}")
        text = str(value or "").strip()
        if text:
            reasons[name] = text
    return reasons


def _normalise_weights(raw: Any) -> dict[str, float]:
    if raw in (None, {}):
        return dict(DEFAULT_TRIAGE_WEIGHTS)
    if not isinstance(raw, dict):
        raise ValueError("triage_weights must be a JSON object")
    unknown = sorted(set(raw) - set(KURATE_METRICS))
    if unknown:
        raise ValueError(f"unknown triage-weight metrics: {unknown}")
    weights: dict[str, float] = {}
    for key, value in raw.items():
        number = float(value)
        if number < 0:
            raise ValueError(f"triage weight {key} must be nonnegative")
        if number > 0:
            weights[key] = number
    if not weights:
        raise ValueError("at least one positive triage weight is required")
    total = sum(weights.values())
    return {key: value / total for key, value in weights.items()}


def _metric_composite(metrics: dict[str, float | None], weights: dict[str, float]) -> float:
    available = {
        key: weight
        for key, weight in weights.items()
        if metrics.get(key) is not None
    }
    if not available:
        return 0.5
    total = sum(available.values())
    return sum((metrics[key] or 0.0) / 10.0 * weight for key, weight in available.items()) / total


def normalise_kurate_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalise a public Kurate assessment snapshot.

    The kernel deliberately does not browse the network. A client or external
    adapter captures the public page/API response, then imports this immutable
    snapshot. The result is a discovery signal only.
    """

    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be a JSON object")
    title = _nonempty(snapshot.get("title"), "title")
    primary_uri = _nonempty(snapshot.get("primary_uri"), "primary_uri")
    kurate_uri = _nonempty(snapshot.get("kurate_uri"), "kurate_uri")
    if "kurate.org/" not in kurate_uri.lower():
        raise ValueError("kurate_uri must point to kurate.org")

    metrics = _normalise_metrics(snapshot.get("metrics"))
    reasons = _normalise_reasons(snapshot.get("reasons"))
    weights = _normalise_weights(snapshot.get("triage_weights"))
    relevance = clamp_score(snapshot.get("relevance_score"), default=0.5)
    metric_composite = _metric_composite(metrics, weights)
    triage_score = 0.75 * metric_composite + 0.25 * relevance

    categories_raw = snapshot.get("categories") or []
    if not isinstance(categories_raw, list):
        raise ValueError("categories must be a JSON list")
    categories = sorted({str(item).strip() for item in categories_raw if str(item).strip()})

    ranks = snapshot.get("ranks") or {}
    if not isinstance(ranks, dict):
        raise ValueError("ranks must be a JSON object")

    model = str(snapshot.get("assessment_model") or "").strip()
    prompt_version = str(snapshot.get("prompt_version") or "").strip()
    assessment_summary = str(snapshot.get("assessment_summary") or "").strip()
    captured_at = str(snapshot.get("captured_at") or "").strip()
    identifier = str(snapshot.get("identifier") or "").strip()
    extra = snapshot.get("metadata") or {}
    if not isinstance(extra, dict):
        raise ValueError("metadata must be a JSON object")

    assessment_body = {
        "metrics": metrics,
        "reasons": reasons,
        "assessment_summary": assessment_summary,
        "assessment_model": model,
        "prompt_version": prompt_version,
        "ranks": ranks,
    }
    assessment_hash = sha256_ref(canonical_json(assessment_body).encode("utf-8"))

    return {
        "schema": "research_kernel/kurate_discovery_signal/v1",
        "provider": "kurate",
        "signal_class": "discovery_only",
        "promotion_eligible": False,
        "title": title,
        "identifier": identifier,
        "primary_uri": primary_uri,
        "kurate_uri": kurate_uri,
        "categories": categories,
        "captured_at": captured_at,
        "assessment_model": model,
        "prompt_version": prompt_version,
        "assessment_summary": assessment_summary,
        "metrics": metrics,
        "reasons": reasons,
        "ranks": ranks,
        "relevance_score": round(relevance, 6),
        "triage_weights": weights,
        "metric_composite": round(metric_composite, 6),
        "triage_score": round(triage_score, 6),
        "assessment_hash": assessment_hash,
        "metadata": extra,
        "limitations": [
            "Kurate is an AI-assisted discovery signal, not peer review.",
            "The assessment cannot verify that experiments or proofs occurred as described.",
            "Scores must not satisfy Research Kernel support, provenance, replay, or promotion gates for another claim.",
            "The primary paper must be independently retrieved and assessed before evidentiary use.",
        ],
    }


def import_kurate_signal(
    kernel: ResearchKernel,
    *,
    run_id: str,
    snapshot: dict[str, Any],
    target_atom_ids: list[str] | None = None,
    atom_id: str = "",
) -> dict[str, Any]:
    normalised = normalise_kurate_snapshot(snapshot)
    target_atom_ids = [str(item).strip() for item in (target_atom_ids or []) if str(item).strip()]

    novelty = (normalised["metrics"].get("novelty") or 5.0) / 10.0
    refutation = (normalised["metrics"].get("refutation_value") or 5.0) / 10.0
    content = f"Literature candidate: {normalised['title']}"
    if normalised["assessment_summary"]:
        content += f" — {normalised['assessment_summary'][:500]}"

    atom = kernel.atom_add(
        run_id=run_id,
        atom_type="OBSERVATION",
        content=content,
        status="CANDIDATE",
        evidence_score=0.0,
        novelty_score=novelty,
        refutability_score=refutation,
        importance_score=normalised["triage_score"],
        uncertainty_score=0.75,
        source_refs=[normalised["primary_uri"], normalised["kurate_uri"]],
        tags=[*DISCOVERY_TAGS, *normalised["categories"]],
        metadata={"kurate": normalised},
        atom_id=atom_id,
    )["atom"]

    evidence = kernel.evidence_attach(
        run_id=run_id,
        atom_id=atom["id"],
        source_type=DISCOVERY_SOURCE_TYPE,
        source_uri=normalised["kurate_uri"],
        summary=(
            "Imported Kurate AI assessment for literature triage only. "
            "Independently retrieve the primary paper before using it as evidence."
        ),
        reliability=0.35,
        artifact_text=canonical_json(normalised),
        metadata={
            "provider": "kurate",
            "signal_class": "discovery_only",
            "promotion_eligible": False,
            "primary_uri": normalised["primary_uri"],
            "assessment_hash": normalised["assessment_hash"],
        },
    )

    links = []
    for target_atom_id in target_atom_ids:
        links.append(
            kernel.link(
                run_id=run_id,
                source_atom_id=atom["id"],
                target_atom_id=target_atom_id,
                edge_type="ANALOGIZES",
                rationale=(
                    "Kurate surfaced this paper as a literature candidate. "
                    "This edge has discovery value only and carries no evidentiary force."
                ),
            )["edge"]
        )

    return {
        "ok": True,
        "candidate_atom": atom,
        "discovery_evidence": evidence,
        "links": links,
        "triage": {
            "score": normalised["triage_score"],
            "metric_composite": normalised["metric_composite"],
            "relevance_score": normalised["relevance_score"],
        },
        "promotion_boundary": {
            "eligible_as_claim_support": False,
            "required_next_step": "retrieve_and_review_primary_paper",
        },
    }


def list_kurate_candidates(
    kernel: ResearchKernel,
    *,
    run_id: str,
    minimum_triage_score: float = 0.0,
    target_atom_id: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    threshold = clamp_score(minimum_triage_score)
    graph = kernel.graph(run_id)
    linked: set[str] | None = None
    if target_atom_id:
        linked = set()
        for edge in graph["edges"]:
            if edge["edge_type"] != "ANALOGIZES":
                continue
            if edge["target_atom_id"] == target_atom_id:
                linked.add(edge["source_atom_id"])
            elif edge["source_atom_id"] == target_atom_id:
                linked.add(edge["target_atom_id"])

    candidates = []
    for atom in graph["atoms"]:
        kurate = atom.get("metadata", {}).get("kurate")
        if not isinstance(kurate, dict) or kurate.get("signal_class") != "discovery_only":
            continue
        if linked is not None and atom["id"] not in linked:
            continue
        score = float(kurate.get("triage_score", 0.0))
        if score < threshold:
            continue
        candidates.append(
            {
                "atom_id": atom["id"],
                "title": kurate.get("title"),
                "primary_uri": kurate.get("primary_uri"),
                "kurate_uri": kurate.get("kurate_uri"),
                "categories": kurate.get("categories", []),
                "triage_score": score,
                "metrics": kurate.get("metrics", {}),
                "assessment_hash": kurate.get("assessment_hash"),
                "next_action": "independently retrieve and assess the primary paper",
            }
        )
    candidates.sort(key=lambda item: (item["triage_score"], item["atom_id"]), reverse=True)
    return {
        "ok": True,
        "run_id": run_id,
        "target_atom_id": target_atom_id or None,
        "minimum_triage_score": threshold,
        "candidates": candidates[: max(1, min(100, int(limit)))],
    }


def kurate_verification_plan(kernel: ResearchKernel, candidate_atom_id: str) -> dict[str, Any]:
    atom = kernel.get_atom(candidate_atom_id)
    kurate = atom.get("metadata", {}).get("kurate")
    if not isinstance(kurate, dict) or kurate.get("provider") != "kurate":
        raise ValueError("atom is not a Kurate literature candidate")
    return {
        "ok": True,
        "candidate_atom_id": candidate_atom_id,
        "title": kurate["title"],
        "primary_uri": kurate["primary_uri"],
        "steps": [
            {
                "id": "identity",
                "action": "Resolve the primary paper and verify title, authors, identifier, and version.",
                "gate": "paper_identity_matches_candidate",
            },
            {
                "id": "primary_read",
                "action": "Read the full primary paper, not only the Kurate assessment.",
                "gate": "primary_text_reviewed",
            },
            {
                "id": "claim_extract",
                "action": "Extract exact claims, hypotheses, assumptions, methods, and limitations into typed Research Kernel atoms.",
                "gate": "claims_are_source_bound",
            },
            {
                "id": "independent_assessment",
                "action": "Independently assess rigor, evidence, novelty overlap, and relevance; record disagreements with Kurate.",
                "gate": "independent_review_complete",
            },
            {
                "id": "evidence_attach",
                "action": "Attach the primary paper to the relevant claim with source_type='paper'; never attach the Kurate score as claim support.",
                "gate": "primary_evidence_attached",
            },
            {
                "id": "contradiction_search",
                "action": "Retrieve prior failures and contradictory evidence before promotion.",
                "gate": "contradiction_search_done",
            },
        ],
        "non_claims": [
            "A high Kurate novelty score does not establish academic novelty.",
            "A high rigor or evidence score does not verify the paper's proofs or experiments.",
            "The Kurate assessment cannot by itself promote or refute a Research Kernel claim.",
        ],
    }
