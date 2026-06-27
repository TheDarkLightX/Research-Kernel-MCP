#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import Context, FastMCP
except Exception:  # pragma: no cover
    Context = Any  # type: ignore
    FastMCP = None  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from internal.research_kernel_mcp.kernel import (  # noqa: E402
    ResearchKernel,
    parse_json_list,
    parse_json_object,
    pretty_json,
)


mcp = FastMCP("research-kernel") if FastMCP is not None else None


def _decorator_passthrough(*_args: Any, **_kwargs: Any):
    def _wrap(fn):
        return fn

    return _wrap


_tool = mcp.tool if mcp is not None else _decorator_passthrough
_resource = mcp.resource if mcp is not None else _decorator_passthrough
_prompt = mcp.prompt if mcp is not None else _decorator_passthrough


def _kernel() -> ResearchKernel:
    return ResearchKernel.from_env()


async def _progress(ctx: Context | None, message: str) -> None:
    if ctx is not None:
        await ctx.report_progress(1, 1, message)


def _json(obj: Any) -> str:
    return pretty_json(obj)


@_tool()
async def rk_start(
    ctx: Context,
    goal: str,
    title: str = "",
    constraints_json: str = "",
    budget_json: str = "",
    domain: str = "",
    success_criteria: str = "",
    metadata_json: str = "",
    run_id: str = "",
) -> str:
    """Create or resume a durable research run."""
    out = _kernel().start_run(
        goal=goal,
        title=title,
        constraints=parse_json_object(constraints_json, field="constraints_json"),
        budget=parse_json_object(budget_json, field="budget_json"),
        domain=domain,
        success_criteria=success_criteria,
        metadata=parse_json_object(metadata_json, field="metadata_json"),
        run_id=run_id,
    )
    await _progress(ctx, f"Run ready: {out['run']['id']}")
    return _json(out)


@_tool()
async def rk_atom_add(
    ctx: Context,
    run_id: str,
    atom_type: str,
    content: str,
    status: str = "UNKNOWN",
    confidence: float | None = None,
    evidence_score: float = 0.0,
    novelty_score: float = 0.5,
    refutability_score: float = 0.5,
    importance_score: float = 0.5,
    uncertainty_score: float = 0.5,
    source_refs_json: str = "",
    artifact_refs_json: str = "",
    parent_ids_json: str = "",
    tags_json: str = "",
    metadata_json: str = "",
    atom_id: str = "",
) -> str:
    """Add a typed public research atom: claim, evidence, question, result, risk, and related types."""
    out = _kernel().atom_add(
        run_id=run_id,
        atom_type=atom_type,
        content=content,
        status=status,
        confidence=confidence,
        evidence_score=evidence_score,
        novelty_score=novelty_score,
        refutability_score=refutability_score,
        importance_score=importance_score,
        uncertainty_score=uncertainty_score,
        source_refs=[str(x) for x in parse_json_list(source_refs_json, field="source_refs_json")],
        artifact_refs=[str(x) for x in parse_json_list(artifact_refs_json, field="artifact_refs_json")],
        parent_ids=[str(x) for x in parse_json_list(parent_ids_json, field="parent_ids_json")],
        tags=[str(x) for x in parse_json_list(tags_json, field="tags_json")],
        metadata=parse_json_object(metadata_json, field="metadata_json"),
        atom_id=atom_id,
    )
    await _progress(ctx, f"Atom added: {out['atom']['id']}")
    return _json(out)


@_tool()
async def rk_link(
    ctx: Context,
    run_id: str,
    source_atom_id: str,
    target_atom_id: str,
    edge_type: str,
    weight: float = 1.0,
    rationale: str = "",
    edge_id: str = "",
) -> str:
    """Add a typed edge between research atoms."""
    out = _kernel().link(
        run_id=run_id,
        source_atom_id=source_atom_id,
        target_atom_id=target_atom_id,
        edge_type=edge_type,
        weight=weight,
        rationale=rationale,
        edge_id=edge_id,
    )
    await _progress(ctx, f"Edge added: {out['edge']['id']}")
    return _json(out)


@_tool()
async def rk_retrieve(
    ctx: Context,
    query: str = "",
    run_id: str = "",
    modes_json: str = "[\"similar_claims\"]",
    atom_id: str = "",
    tags_json: str = "",
    limit: int = 10,
) -> str:
    """Hybrid local retrieval over lexical memory, graph neighbors, failures, contradictions, and frontier atoms."""
    out = _kernel().retrieve(
        query=query,
        run_id=run_id or None,
        modes=[str(x) for x in parse_json_list(modes_json, default=["similar_claims"], field="modes_json")],
        atom_id=atom_id or None,
        tags=[str(x) for x in parse_json_list(tags_json, field="tags_json")],
        limit=limit,
    )
    await _progress(ctx, f"Retrieved {len(out['results'])} atoms")
    return _json(out)


@_tool()
async def rk_morph(
    ctx: Context,
    target: str,
    run_id: str = "",
    modes_json: str = "[\"equivalent_statement\", \"counterexample_search\", \"formal_spec\"]",
    constraints_json: str = "",
    max_candidates: int = 8,
    store: bool = False,
) -> str:
    """Generate Morph-style reformulations for a claim, problem, theorem, design, or benchmark target."""
    out = _kernel().morph(
        target=target,
        run_id=run_id or None,
        modes=[str(x) for x in parse_json_list(modes_json, field="modes_json")],
        constraints=parse_json_object(constraints_json, field="constraints_json"),
        max_candidates=max_candidates,
        store=bool(store),
    )
    await _progress(ctx, f"Morph candidates: {len(out['reformulations'])}")
    return _json(out)


@_tool()
async def rk_refute(
    ctx: Context,
    run_id: str,
    target_atom_id: str,
    strategy: str,
    tests_json: str = "",
    counterexample: str = "",
    counterexample_is_actual: bool = False,
    metadata_json: str = "",
) -> str:
    """Register a refutation plan. Set counterexample_is_actual=true only for a concrete witness."""
    out = _kernel().refute(
        run_id=run_id,
        target_atom_id=target_atom_id,
        strategy=strategy,
        tests=[str(x) for x in parse_json_list(tests_json, field="tests_json")],
        counterexample=counterexample,
        counterexample_is_actual=counterexample_is_actual,
        metadata=parse_json_object(metadata_json, field="metadata_json"),
    )
    await _progress(ctx, f"Refutation atom: {out['refutation_atom']['id']}")
    return _json(out)


@_tool()
async def rk_evidence_attach(
    ctx: Context,
    run_id: str,
    atom_id: str,
    source_type: str,
    source_uri: str = "",
    quote: str = "",
    summary: str = "",
    reliability: float = 0.5,
    artifact_path: str = "",
    artifact_text: str = "",
    metadata_json: str = "",
) -> str:
    """Attach evidence. source_uri, artifact_path, or artifact_text is required for promotion provenance."""
    out = _kernel().evidence_attach(
        run_id=run_id,
        atom_id=atom_id,
        source_type=source_type,
        source_uri=source_uri,
        quote=quote,
        summary=summary,
        reliability=reliability,
        artifact_path=artifact_path,
        artifact_text=artifact_text,
        metadata=parse_json_object(metadata_json, field="metadata_json"),
    )
    await _progress(ctx, f"Evidence attached: {out['evidence']['id']}")
    return _json(out)


@_tool()
async def rk_score(ctx: Context, atom_id: str) -> str:
    """Score an atom with the deterministic research-utility rubric."""
    out = _kernel().score_atom(atom_id)
    await _progress(ctx, f"Score: {out['priority']}")
    return _json(out)


@_tool()
async def rk_frontier(ctx: Context, run_id: str, limit: int = 10) -> str:
    """Return highest-value next research tasks for a run."""
    out = _kernel().frontier(run_id=run_id, limit=limit)
    await _progress(ctx, f"Frontier: {len(out['frontier'])}")
    return _json(out)


@_tool()
async def rk_promote(
    ctx: Context,
    claim_atom_id: str,
    to_status: str,
    rationale: str,
    checks_json: str = "",
) -> str:
    """Fail-closed claim promotion gate. SUPPORTED requires evidence, refutation, dependencies, provenance, contradiction search, replay where applicable, and rationale."""
    out = _kernel().promote(
        claim_atom_id=claim_atom_id,
        to_status=to_status,
        rationale=rationale,
        checks=parse_json_object(checks_json, field="checks_json"),
    )
    await _progress(ctx, f"Promotion gate: {'passed' if out['ok'] else 'rejected'}")
    return _json(out)


@_tool()
async def rk_report(ctx: Context, run_id: str, include_graph: bool = False) -> str:
    """Generate a structured research snapshot: claims, failures, contradictions, frontier, and non-claims."""
    out = _kernel().report(run_id=run_id, include_graph=bool(include_graph))
    await _progress(ctx, "Report generated")
    return _json(out)


@_resource("rk://runs/{run_id}/summary", name="Research run summary", mime_type="application/json")
def rk_resource_run_summary(run_id: str) -> str:
    return _json(_kernel().run_summary(run_id))


@_resource("rk://runs/{run_id}/graph", name="Research run graph", mime_type="application/json")
def rk_resource_run_graph(run_id: str) -> str:
    return _json(_kernel().graph(run_id))


@_resource("rk://runs/{run_id}/frontier", name="Research run frontier", mime_type="application/json")
def rk_resource_run_frontier(run_id: str) -> str:
    return _json(_kernel().frontier(run_id=run_id, limit=25))


@_resource("rk://atoms/{atom_id}", name="Research atom", mime_type="application/json")
def rk_resource_atom(atom_id: str) -> str:
    return _json({"ok": True, "atom": _kernel().get_atom(atom_id)})


@_resource("rk://claims/{claim_id}", name="Research claim", mime_type="application/json")
def rk_resource_claim(claim_id: str) -> str:
    atom = _kernel().get_atom(claim_id)
    if atom["type"] not in {"CLAIM", "HYPOTHESIS"}:
        return _json({"ok": False, "error": "atom_is_not_claim_or_hypothesis", "atom": atom})
    return _json({"ok": True, "claim": atom, "score": _kernel().score_atom(claim_id)})


@_resource("rk://artifacts/{artifact_hash}", name="Research artifact", mime_type="application/json")
def rk_resource_artifact(artifact_hash: str) -> str:
    return _json(_kernel().artifact(artifact_hash))


@_resource("rk://memory/similar/{query}", name="Research memory similar", mime_type="application/json")
def rk_resource_memory_similar(query: str) -> str:
    return _json(_kernel().retrieve(query=query, modes=["similar_claims", "prior_failures"], limit=20))


@_resource("rk://memory/contradictions/{claim_id}", name="Research memory contradictions", mime_type="application/json")
def rk_resource_memory_contradictions(claim_id: str) -> str:
    return _json(_kernel().retrieve(atom_id=claim_id, modes=["graph_neighbors", "contradictory_evidence"], limit=20))


@_resource("rk://reports/latest", name="Latest research report", mime_type="application/json")
def rk_resource_latest_report() -> str:
    return _json(_kernel().latest_report())


@_prompt(name="research.kernel_mode", description="Operate as an evidence-first Research Kernel MCP client.")
def prompt_kernel_mode() -> str:
    return """You are using Research Kernel MCP.

Do not treat private reasoning as an artifact. Externalize only concise, auditable research atoms: claims, hypotheses, observations, evidence, counterexamples, reformulations, experiments, results, risks, and decisions.

For complex research:
1. Start or resume a run.
2. Retrieve similar prior work and prior failures.
3. Add candidate atoms.
4. Use Morph reformulation before settling on one framing.
5. Attach evidence or artifacts for claims.
6. Try to refute important claims.
7. Promote claims only through the PopperPad-style gate.
8. Keep unsupported claims UNKNOWN.
9. Ask for frontier tasks when stuck.
10. Produce reports from the research graph, not from memory alone.
"""


@_prompt(name="research.start", description="Start a scoped research run.")
def prompt_research_start(goal: str = "", domain: str = "") -> str:
    return f"""Start a Research Kernel run for this goal:
{goal}

Domain: {domain}

Use rk_start, then retrieve similar prior work and prior failures before adding candidate atoms."""


@_prompt(name="research.decompose", description="Decompose a problem into public research atoms.")
def prompt_research_decompose(problem: str = "") -> str:
    return f"""Decompose this into ResearchAtom entries without exposing private reasoning:
{problem}

Create observations, questions, hypotheses, risks, and open problems. Link dependencies explicitly."""


@_prompt(name="research.refute", description="Design a refutation plan.")
def prompt_research_refute(claim: str = "") -> str:
    return f"""Design a refutation plan for:
{claim}

Prefer smallest counterexample search, adversarial tests, benchmark pressure, proof-obligation failure, and contradiction retrieval."""


@_prompt(name="research.morph", description="Generate Morph-style reformulations.")
def prompt_research_morph(target: str = "") -> str:
    return f"""Use rk_morph on this target:
{target}

Include equivalent, weaker, counterexample-search, formal-spec, benchmark-proxy, and attack-surface modes when relevant."""


@_prompt(name="research.evidence_review", description="Review evidence before promotion.")
def prompt_evidence_review(claim_id: str = "") -> str:
    return f"""Review evidence for claim atom {claim_id}.

Check support evidence, refutation attempts, dependencies, provenance, contradiction search, replay recipes, and non-claims before calling rk_promote."""


@_prompt(name="research.promote_claim", description="Run the fail-closed promotion gate.")
def prompt_promote_claim(claim_id: str = "") -> str:
    return f"""Promote claim atom {claim_id} only if the Research Kernel gate passes.

SUPPORTED requires explicit support evidence, refutation attempt, dependencies, provenance, contradiction search, replay recipe when applicable, and rationale."""


@_prompt(name="research.report", description="Produce a research graph report.")
def prompt_report(run_id: str = "") -> str:
    return f"""Call rk_report for run {run_id}. Summarize supported claims, refuted claims, contradictions, frontier tasks, and non-claims."""


@_prompt(name="research.next_frontier", description="Select the next high-value research action.")
def prompt_next_frontier(run_id: str = "") -> str:
    return f"""Call rk_frontier for run {run_id}, choose the highest-value task, retrieve prior failures, and add the next evidence or refutation atom."""


def _self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="research-kernel-self-test-") as tmp:
        return ResearchKernel(Path(tmp)).self_test()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Research Kernel MCP server")
    parser.add_argument("--self-test", action="store_true", help="Run a deterministic backend self-test and exit")
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="stdio")
    parser.add_argument("--mount-path", default=None)
    args = parser.parse_args()

    if args.self_test:
        print(_json(_self_test()))
        raise SystemExit(0)

    if mcp is None:
        print(json.dumps({"ok": False, "error": "mcp_fastmcp_not_installed"}, sort_keys=True))
        raise SystemExit(1)
    mcp.run(transport=args.transport, mount_path=args.mount_path)
