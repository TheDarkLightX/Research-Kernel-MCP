#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from internal.research_kernel_mcp.kernel import ResearchKernel, canonical_json

RUN_ID = "run_zenodex_functional_core_v1"


def atom(
    kernel: ResearchKernel,
    *,
    atom_id: str,
    atom_type: str,
    content: str,
    status: str,
    importance: float,
    uncertainty: float,
    refutability: float = 0.8,
    novelty: float = 0.5,
    parents: list[str] | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return kernel.atom_add(
        run_id=RUN_ID,
        atom_id=atom_id,
        atom_type=atom_type,
        content=content,
        status=status,
        importance_score=importance,
        uncertainty_score=uncertainty,
        refutability_score=refutability,
        novelty_score=novelty,
        parent_ids=parents or [],
        tags=tags or [],
        metadata=metadata or {},
    )["atom"]


def attach(
    kernel: ResearchKernel,
    atom_id: str,
    *,
    source_type: str,
    source_uri: str,
    summary: str,
    artifact_text: str,
    reliability: float,
) -> None:
    kernel.evidence_attach(
        run_id=RUN_ID,
        atom_id=atom_id,
        source_type=source_type,
        source_uri=source_uri,
        summary=summary,
        artifact_text=artifact_text,
        reliability=reliability,
    )


def build_run(output: Path) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    kernel = ResearchKernel(output / "kernel")
    kernel.start_run(
        run_id=RUN_ID,
        title="ZenoDEX functional-core assurance continuation",
        goal=(
            "Identify the strongest next ZenoDEX functional-core assurance moves by combining "
            "formal parser and parallel-execution results, bounded model checking, reformulation "
            "search, and the remaining differential-audit obligations."
        ),
        domain="formal methods, deterministic systems, AMM economics",
        constraints={
            "normative_core": "integer-only pure transition",
            "parallelism": "same immutable snapshot; certified independence; canonical join",
            "promotion": "fail closed; exact-source evidence; explicit nonclaims",
            "tool_roles": {
                "research_kernel": "evidence graph and promotion gate",
                "morph": "advisory reformulation discovery until strict replay",
                "esso": "finite bounded counterexample and invariant oracle",
                "lean": "small-kernel theorem checking",
            },
        },
        success_criteria=(
            "A ranked, refutable frontier with at least one supported scoped formal claim, "
            "two concrete counterexamples to overbroad claims, and executable next experiments."
        ),
        metadata={
            "zenodex_pr": 471,
            "zenodex_pr_head": "3c5ee8b7487048a2dd0a370a64eeb1c294cd9c04",
            "research_kernel_source": "d9cdfceaa396dd56acfacbd042b89ce633dbc173",
            "morph_source": "a26a9f5ddabfa2d5be8e12f8c3546836ace92520",
            "esso_source": "db8a3f8a782a508ada5005a2cf177f25c58f451d",
        },
    )

    theorem = atom(
        kernel,
        atom_id="result_parser_lean_v1",
        atom_type="RESULT",
        content=(
            "At ZenoDEX PR 471 head 3c5ee8b, Lean checked the abstract theorems that a "
            "deterministic full-consumption parser has a unique result and a decoder round trip "
            "makes the encoder injective; the new proof surface contains no sorry, admit, or axiom."
        ),
        status="SUPPORTED",
        importance=0.85,
        uncertainty=0.1,
        tags=["lean", "parser", "canonical-encoding", "scoped-result"],
    )
    attach(
        kernel,
        theorem["id"],
        source_type="proof",
        source_uri=(
            "https://github.com/TheDarkLightX/ZenoDEX/blob/"
            "3c5ee8b7487048a2dd0a370a64eeb1c294cd9c04/"
            "lean-mathlib/Proofs/TypedDeterministicParser.lean"
        ),
        summary="Exact-source Lean theorem file and successful exact-head workflow evidence.",
        artifact_text=(
            "Scope: abstract Parser Token Output := List Token -> Option ParseResult. "
            "Checked obligations: accepts_unique, acceptsAll_unique, canonicalAcceptance_unique, "
            "encode_injective_of_roundtrip. Nonclaim: no runtime decoder refinement is established."
        ),
        reliability=0.95,
    )

    parser_claim = atom(
        kernel,
        atom_id="claim_typed_parser_boundary",
        atom_type="CLAIM",
        content=(
            "For a ZenoDEX authority surface, typed deterministic parser combinators are useful "
            "only when the concrete decoder additionally proves bounded full consumption, exact "
            "canonical re-encoding, stable typed errors, and cross-language byte parity."
        ),
        status="TESTABLE",
        importance=0.95,
        uncertainty=0.2,
        parents=[theorem["id"]],
        tags=["parser", "authority-boundary", "refinement"],
    )
    attach(
        kernel,
        parser_claim["id"],
        source_type="support",
        source_uri="https://github.com/TheDarkLightX/ZenoDEX/pull/469",
        summary="Canonical-wire PR supplies concrete duplicate-key, spelling, and receipt-carrier witnesses.",
        artifact_text=(
            "Required runtime test: decode(bytes)=value and encode(value)=bytes for every accepted "
            "authority payload, in Python, Rust, Tau adapter, and proof guest."
        ),
        reliability=0.85,
    )
    attach(
        kernel,
        parser_claim["id"],
        source_type="contradiction_search",
        source_uri="https://github.com/TheDarkLightX/ZenoDEX/pull/469",
        summary="Search for accepted alternate spellings, duplicate keys, partial parses, and cross-language drift.",
        artifact_text=(
            "No contradiction to the scoped claim was recorded. This is not evidence that every "
            "authority decoder already satisfies the premises."
        ),
        reliability=0.65,
    )

    parallel_claim = atom(
        kernel,
        atom_id="claim_parallel_equivalence",
        atom_type="CLAIM",
        content=(
            "Deterministic parallel ZenoDEX execution requires workers to evaluate against one "
            "immutable pre-state, sound read/write/context footprints, commuting complete patches, "
            "canonical rejection/effect ordering, a fixed reduction semantics, and one expected-root "
            "atomic commit; disjoint write sets alone are insufficient."
        ),
        status="TESTABLE",
        importance=1.0,
        uncertainty=0.25,
        tags=["parallelism", "commutation", "linearizability", "fcis"],
    )
    attach(
        kernel,
        parallel_claim["id"],
        source_type="proof",
        source_uri=(
            "https://github.com/TheDarkLightX/ZenoDEX/blob/"
            "3c5ee8b7487048a2dd0a370a64eeb1c294cd9c04/"
            "lean-mathlib/Proofs/DeterministicParallelExecution.lean"
        ),
        summary="Lean proves disjoint immutable patch commutation, permutation invariance, and abstract CAS behavior.",
        artifact_text=(
            "Unclosed runtime premises: footprint soundness, common pre-state, complete patch extraction, "
            "canonical error order, exact effect/receipt equality, and storage linearizability."
        ),
        reliability=0.95,
    )

    naive_parallel = atom(
        kernel,
        atom_id="claim_disjoint_writes_suffice",
        atom_type="CLAIM",
        content="Disjoint write sets alone guarantee equivalence of parallel and sequential ZenoDEX execution.",
        status="REFUTED",
        importance=0.9,
        uncertainty=0.0,
        tags=["parallelism", "counterexample"],
    )
    rw_counterexample = atom(
        kernel,
        atom_id="counterexample_read_write_hazard",
        atom_type="COUNTEREXAMPLE",
        content=(
            "Let state x=0,y=0. Task A reads x and writes y:=x. Task B writes x:=1. Their write "
            "sets {y} and {x} are disjoint, but A;B yields y=0 while B;A yields y=1."
        ),
        status="SUPPORTED",
        importance=1.0,
        uncertainty=0.0,
        tags=["read-write-hazard", "parallelism"],
    )
    kernel.link(
        run_id=RUN_ID,
        source_atom_id=rw_counterexample["id"],
        target_atom_id=naive_parallel["id"],
        edge_type="REFUTES",
        edge_id="edge_rw_counterexample_refutes",
        rationale="A read/write dependency changes the sequential result despite disjoint writes.",
    )

    matching_claim = atom(
        kernel,
        atom_id="claim_matching_needs_canonical_winner",
        atom_type="CLAIM",
        content=(
            "A deterministic matching procedure is not by itself a consensus specification; ZenoDEX "
            "must bind a unique objective, candidate domain, normalization, and tie-break so every "
            "conforming implementation returns the same allocation."
        ),
        status="TESTABLE",
        importance=0.85,
        uncertainty=0.2,
        tags=["matching", "batch-clearing", "canonical-winner"],
    )
    naive_matching = atom(
        kernel,
        atom_id="claim_any_matching_is_canonical",
        atom_type="CLAIM",
        content="Any deterministic algorithm for bipartite matching yields a canonical ZenoDEX settlement.",
        status="REFUTED",
        importance=0.7,
        uncertainty=0.0,
        tags=["matching", "counterexample"],
    )
    match_counterexample = atom(
        kernel,
        atom_id="counterexample_multiple_perfect_matchings",
        atom_type="COUNTEREXAMPLE",
        content=(
            "The complete bipartite graph K2,2 has two perfect matchings with equal cardinality. Two "
            "deterministic implementations using different vertex orders can return different valid "
            "matchings unless the protocol specifies canonical ordering or a unique weighted optimum."
        ),
        status="SUPPORTED",
        importance=0.8,
        uncertainty=0.0,
        tags=["matching", "tie-break"],
    )
    kernel.link(
        run_id=RUN_ID,
        source_atom_id=match_counterexample["id"],
        target_atom_id=naive_matching["id"],
        edge_type="REFUTES",
        edge_id="edge_matching_counterexample_refutes",
        rationale="Existence and deterministic construction do not imply implementation-independent uniqueness.",
    )
    kernel.link(
        run_id=RUN_ID,
        source_atom_id=match_counterexample["id"],
        target_atom_id=matching_claim["id"],
        edge_type="SUPPORTS",
        edge_id="edge_matching_counterexample_supports",
        rationale="Multiple optima demonstrate the need for a canonical objective and tie-break.",
    )

    economics = atom(
        kernel,
        atom_id="claim_economic_lifecycle_frontier",
        atom_type="CLAIM",
        content=(
            "After aliasing, canonical encoding, debt-cap, finalized-Oracle, and owner-lifecycle repairs, "
            "the dominant functional-core risk is incomplete economic lifecycle semantics: redemption "
            "ordering, partial Stability Pool offset, residual insolvency and redistribution, Recovery "
            "Mode, shutdown, and exact fee claimant custody."
        ),
        status="UNDER_TEST",
        importance=1.0,
        uncertainty=0.35,
        tags=["zusd", "audit", "economic-lifecycle"],
    )
    attach(
        kernel,
        economics["id"],
        source_type="source",
        source_uri="https://zenodex-oracle-audit-v4.jazzy-harp-9002.chatgpt.site/?view=registry",
        summary="Differential-audit registry and prior closure ledger identify the remaining economic families.",
        artifact_text=(
            "Next bounded models should target one lifecycle at a time and preserve exact no-op rejection, "
            "conservation, owner/claimant authority, debt floors, and terminal representability."
        ),
        reliability=0.75,
    )

    tools_claim = atom(
        kernel,
        atom_id="claim_tool_role_separation",
        atom_type="DECISION",
        content=(
            "Use Morph to generate reformulation candidates, ESSO to search finite bounded transition "
            "systems for counterexamples and inductive invariants, Lean to check connective theorems, "
            "and Research Kernel to retain evidence and block overbroad promotion."
        ),
        status="CANDIDATE",
        importance=0.9,
        uncertainty=0.2,
        tags=["architecture", "research-tools", "assurance"],
    )
    attach(
        kernel,
        tools_claim["id"],
        source_type="source",
        source_uri="https://github.com/TheDarkLightX/Research-Kernel-MCP",
        summary="Research Kernel explicitly separates deterministic evidence state from creative model work.",
        artifact_text=(
            "Morph reformulations remain candidates until domain checks and strict replay. ESSO results are "
            "bounded to the declared finite model. Neither tool silently upgrades a production claim."
        ),
        reliability=0.9,
    )

    experiments = [
        (
            "experiment_parser_refinement",
            parser_claim["id"],
            "Generate source-derived authority grammars and prove parser/encoder round trips for every value-moving surface across Python and Rust.",
        ),
        (
            "experiment_footprint_differential",
            parallel_claim["id"],
            "Instrument every command to record actual reads/writes and reject any execution whose trace exceeds the declared footprint; then compare parallel and normative sequential bytes.",
        ),
        (
            "experiment_zusd_lifecycle_models",
            economics["id"],
            "Build separate ESSO models for partial liquidation, redistribution, Recovery Mode, redemption ordering, and shutdown; require multi-solver UNSAT for invariant violations.",
        ),
        (
            "experiment_matching_certificate",
            matching_claim["id"],
            "Define a finite canonical candidate set and lexicographic objective, then prove winner uniqueness and replay the selected allocation through the sequential core.",
        ),
    ]
    for experiment_id, target_id, content in experiments:
        exp = atom(
            kernel,
            atom_id=experiment_id,
            atom_type="EXPERIMENT",
            content=content,
            status="TESTABLE",
            importance=0.9,
            uncertainty=0.35,
            tags=["next-experiment"],
        )
        kernel.link(
            run_id=RUN_ID,
            source_atom_id=exp["id"],
            target_atom_id=target_id,
            edge_type="TESTS",
            edge_id=f"edge_{experiment_id}_tests",
            rationale="Executable experiment for the associated scoped claim.",
        )

    morph_results = {
        "parallel": kernel.morph(
            target=parallel_claim["content"],
            run_id=RUN_ID,
            modes=["equivalent_statement", "counterexample_search", "formal_spec", "invariant_form"],
            constraints={"integer_only": True, "atomic_commit": True},
            max_candidates=8,
            store=True,
        ),
        "economics": kernel.morph(
            target=economics["content"],
            run_id=RUN_ID,
            modes=["decomposition", "counterexample_search", "formal_spec", "benchmark_form"],
            constraints={"one_lifecycle_per_model": True, "bounded_domains": True},
            max_candidates=8,
            store=True,
        ),
    }

    promotion = kernel.promote(
        claim_atom_id=parser_claim["id"],
        to_status="SUPPORTED",
        rationale=(
            "Scoped support only: abstract Lean uniqueness/injectivity theorems compiled, concrete canonical-wire "
            "witnesses exist, a contradiction-search plan is recorded, and the runtime-refinement nonclaim remains explicit."
        ),
        checks={
            "contradiction_search_done": True,
            "replay_required": True,
            "replay_recipe": (
                "Rebuild ZenoDEX PR 471 exact head; type-check TypedDeterministicParser.lean; run PR 469 canonical-wire vectors."
            ),
        },
    )

    report = kernel.report(run_id=RUN_ID, include_graph=True)
    frontier = kernel.frontier(run_id=RUN_ID, limit=25)
    summary = kernel.run_summary(RUN_ID)

    decision_view = {
        "schema": "zenodex.research_kernel.functional_core_decision.v1",
        "supported_scoped_claim": parser_claim["id"] if promotion.get("ok") else None,
        "refuted_overbroad_claims": [naive_parallel["id"], naive_matching["id"]],
        "highest_priority_frontier": [
            {
                "atom_id": item["atom_id"],
                "priority": item["priority"],
                "next_action": item["next_action"],
            }
            for item in frontier["frontier"][:10]
        ],
        "recommended_sequence": [
            "source-derived typed authority grammars and concrete round-trip refinement",
            "sound read/write/context footprints with dynamic trace containment tests",
            "atomic state/effect/receipt/nonce/outbox commit",
            "bounded zUSD lifecycle models before implementation",
            "canonical matching/allocation certificates only after candidate-domain completeness",
        ],
        "nonclaims": [
            "the runtime parser refinement is not complete",
            "arbitrary ZenoDEX parallel execution is not proved deterministic",
            "ESSO bounded verification does not prove unbounded production behavior",
            "Morph retrieval does not authorize a theorem or design",
            "the full differential-audit registry is not closed",
        ],
    }
    decision_hash = hashlib.sha256(canonical_json(decision_view).encode("utf-8")).hexdigest()
    decision_view["sha256"] = decision_hash

    outputs = {
        "research_report.json": report,
        "frontier.json": frontier,
        "run_summary.json": summary,
        "morph_candidates.json": morph_results,
        "promotion.json": promotion,
        "decision.json": decision_view,
    }
    for name, obj in outputs.items():
        (output / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return decision_view


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    decision = build_run(args.output)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
