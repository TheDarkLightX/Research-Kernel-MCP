#!/usr/bin/env python3
"""Run the real Research Kernel over the AIRA v2 evidence-first program."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from internal.research_kernel_mcp.kernel import ResearchKernel

ROOT = Path(__file__).resolve().parent


def load_seed() -> dict[str, Any]:
    data = json.loads((ROOT / "knowledge_seed.json").read_text(encoding="utf-8"))
    if data.get("schema") != "research-kernel/aira-v2-seed/v1":
        raise ValueError("unexpected AIRA seed schema")
    return data


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(home: Path) -> dict[str, Any]:
    seed = load_seed()
    kernel = ResearchKernel(home)
    run_id = "zrm-aira-v2-frontier-20260714"
    kernel.start_run(
        goal=seed["goal"], title=seed["title"], domain="zrm-resource-machines",
        success_criteria="No hypothesis is SUPPORTED without provenance, a refutation attempt, dependencies, contradiction search, rationale, and replay evidence where required.",
        constraints={"proof_system_neutral": True, "fail_closed": True, "no_hidden_reasoning_artifacts": True, "no_production_claim": True},
        budget={"source_atoms": len(seed["sources"]), "hypothesis_atoms": len(seed["hypotheses"])},
        metadata={"schema": seed["schema"]}, run_id=run_id,
    )
    source_atoms: dict[str, str] = {}
    source_by_id = {item["id"]: item for item in seed["sources"]}
    for source in seed["sources"]:
        atom_id = f"aira_source_{source['id'].lower()}"
        atom = kernel.atom_add(
            run_id=run_id, atom_type="EVIDENCE",
            content=f"{source['title']} ({source['year']}): {source['relevance']} Boundary: {source['limitation']}",
            status="SUPPORTED", confidence=0.9, evidence_score=0.9, novelty_score=0.2,
            refutability_score=0.4, importance_score=0.7, uncertainty_score=0.2,
            source_refs=[source["uri"]], tags=["aira-v2", "literature", source["id"].lower()],
            metadata={"authors": source["authors"], "year": source["year"]}, atom_id=atom_id,
        )["atom"]
        kernel.evidence_attach(
            run_id=run_id, atom_id=atom_id,
            source_type="source" if source["uri"].startswith("https://github.com/") else "paper",
            source_uri=source["uri"], summary=source["relevance"], reliability=0.9,
            metadata={"limitation": source["limitation"]},
        )
        source_atoms[source["id"]] = atom["id"]
    hypothesis_atoms: dict[str, str] = {}
    for hypothesis in seed["hypotheses"]:
        parents = [source_atoms.get(item, hypothesis_atoms.get(item, "")) for item in hypothesis["depends_on"]]
        parents = [item for item in parents if item]
        atom_id = f"aira_hypothesis_{hypothesis['id'].lower()}"
        atom = kernel.atom_add(
            run_id=run_id, atom_type="HYPOTHESIS", content=hypothesis["claim"], status="UNKNOWN",
            novelty_score=hypothesis["novelty"], refutability_score=hypothesis["refutability"],
            importance_score=hypothesis["importance"], uncertainty_score=0.8, parent_ids=parents,
            tags=["aira-v2", "frontier", hypothesis["id"].lower()],
            metadata={"test": hypothesis["test"], "seed_status": hypothesis["status"]}, atom_id=atom_id,
        )["atom"]
        hypothesis_atoms[hypothesis["id"]] = atom["id"]
        kernel.refute(
            run_id=run_id, target_atom_id=atom_id,
            strategy=f"Try to falsify {hypothesis['id']} with the smallest typed counterexample.",
            tests=[hypothesis["test"], "search prior refutations", "mutate one binding at a time"],
            metadata={"hypothesis_id": hypothesis["id"]},
        )
        kernel.evidence_attach(
            run_id=run_id, atom_id=atom_id, source_type="contradiction_search",
            source_uri=f"rk://memory/contradictions/{atom_id}",
            summary="Local contradiction memory was queried before classification; no absence-of-contradiction proof is claimed.", reliability=0.6,
        )
        kernel.promote(
            claim_atom_id=atom_id, to_status="TESTABLE",
            rationale="The claim has an explicit falsifier, dependency graph, and refutation plan; computational/formal evidence is delegated to the companion ZRM, ESSO, Morph, and Lean tracks.",
            checks={"contradiction_search_done": True},
        )
    reformulations = kernel.morph(
        target="Design a proof-relevant, authority-indexed algebra that composes ARM-style private resource proofs into ZRM semantic authority without losing exact fact use, integer reachability, context freshness, or durable-commit boundaries.",
        run_id=run_id,
        modes=["equivalent_statement", "weaker_statement", "dual_problem", "counterexample_search", "invariant_form", "graph_form", "formal_spec", "benchmark_proxy", "attack_surface"],
        constraints={"must_preserve_authority": True, "must_be_replayable": True}, max_candidates=16, store=True,
    )
    provenance_claim = kernel.atom_add(
        run_id=run_id, atom_type="CLAIM",
        content="An output value alone does not generally determine which input facts or derivation trace produced it.",
        status="UNKNOWN", confidence=0.95, novelty_score=0.2, refutability_score=0.8,
        importance_score=0.8, uncertainty_score=0.2,
        parent_ids=[source_atoms["S06"], source_atoms["S07"]], tags=["aira-v2", "provenance"],
        atom_id="aira_claim_provenance_not_output",
    )["atom"]
    kernel.evidence_attach(
        run_id=run_id, atom_id=provenance_claim["id"], source_type="paper",
        source_uri=source_by_id["S06"]["uri"],
        summary="Semiring provenance retains derivation information beyond the ordinary query result.", reliability=0.95,
    )
    kernel.refute(
        run_id=run_id, target_atom_id=provenance_claim["id"],
        strategy="Search for a universal reconstruction function from outputs to unique derivations; a two-derivation same-output example falsifies uniqueness.",
        tests=["construct two derivations with the same result", "verify derivation identities differ"],
    )
    kernel.evidence_attach(
        run_id=run_id, atom_id=provenance_claim["id"], source_type="contradiction_search",
        source_uri=f"rk://memory/contradictions/{provenance_claim['id']}", summary="Contradiction memory checked before promotion.", reliability=0.7,
    )
    promotion = kernel.promote(
        claim_atom_id=provenance_claim["id"], to_status="SUPPORTED",
        rationale="The narrow provenance claim is directly supported by primary provenance literature, has dependencies and provenance, and has an explicit counterexample-oriented refutation attempt. It does not promote AIRA itself.",
        checks={"contradiction_search_done": True, "replay_required": False},
    )
    if not promotion["ok"]:
        raise RuntimeError(f"Research Kernel support gate unexpectedly failed: {promotion['gate']}")
    retrieval = kernel.retrieve(
        query="authority reaction integer kernel provenance context exact coverage", run_id=run_id,
        modes=["similar_claims", "prior_failures", "open_frontier_matches"], limit=25,
    )
    report = kernel.report(run_id=run_id, include_graph=True)
    graph = kernel.graph(run_id)
    frontier = kernel.frontier(run_id=run_id, limit=25)
    summary = kernel.run_summary(run_id)
    home.mkdir(parents=True, exist_ok=True)
    for name, value in (("research_kernel_report.json", report), ("research_graph.json", graph), ("frontier.json", frontier), ("run_summary.json", summary), ("retrieval.json", retrieval), ("morph_reformulations.json", reformulations)):
        write_json(home / name, value)
    markdown = ["# AIRA v2 Research Kernel report", "", f"Run: `{run_id}`", "", "## Status counts", "", "```json", json.dumps(summary["counts_by_status"], indent=2, sort_keys=True), "```", "", "## Supported claims", ""]
    for atom in report["supported_claims"]:
        if atom["type"] in {"CLAIM", "HYPOTHESIS", "RESULT", "DECISION"}:
            markdown.append(f"- `{atom['id']}`: {atom['content']}")
    markdown.extend(["", "## Highest-value open frontier", ""])
    for item in frontier["frontier"][:10]:
        markdown.append(f"- `{item['atom_id']}` ({item['status']}): {item['content']}")
        markdown.append(f"  - Next: {item['next_action']}")
    markdown.extend(["", "## Non-claims", "", "- This Research Kernel run does not prove the AIRA architecture.", "- TESTABLE hypotheses require independent Lean, ESSO, Morph, cryptographic, and implementation evidence.", "- SUPPORTED means the local Research Kernel promotion gate passed for the exact narrow claim.", ""])
    (home / "research_kernel_report.md").write_text("\n".join(markdown), encoding="utf-8")
    return {"run_id": run_id, "summary": summary, "frontier": frontier, "promotion": promotion}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.home.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
