#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

from internal.research_kernel_mcp import server as base
from internal.research_kernel_mcp.kurate import (
    import_kurate_signal,
    kurate_verification_plan,
    list_kurate_candidates,
)
from internal.research_kernel_mcp.kernel import parse_json_list, parse_json_object


mcp = base.mcp
_tool = base._tool
_prompt = base._prompt


@_tool()
async def rk_kurate_import(
    ctx: base.Context,
    run_id: str,
    snapshot_json: str,
    target_atom_ids_json: str = "",
    atom_id: str = "",
) -> str:
    """Import a public Kurate assessment as a discovery-only literature candidate.

    The snapshot is content-addressed and attached only to the candidate atom.
    It never counts as support, refutation, replay, or provenance for a target
    claim. Independently retrieve the primary paper before evidentiary use.
    """

    out = import_kurate_signal(
        base._kernel(),
        run_id=run_id,
        snapshot=parse_json_object(snapshot_json, field="snapshot_json"),
        target_atom_ids=[
            str(item)
            for item in parse_json_list(
                target_atom_ids_json,
                field="target_atom_ids_json",
            )
        ],
        atom_id=atom_id,
    )
    await base._progress(
        ctx,
        f"Kurate candidate imported: {out['candidate_atom']['id']}",
    )
    return base._json(out)


@_tool()
async def rk_kurate_candidates(
    ctx: base.Context,
    run_id: str,
    minimum_triage_score: float = 0.0,
    target_atom_id: str = "",
    limit: int = 20,
) -> str:
    """List imported Kurate literature candidates by discovery triage score."""

    out = list_kurate_candidates(
        base._kernel(),
        run_id=run_id,
        minimum_triage_score=minimum_triage_score,
        target_atom_id=target_atom_id,
        limit=limit,
    )
    await base._progress(ctx, f"Kurate candidates: {len(out['candidates'])}")
    return base._json(out)


@_tool()
async def rk_kurate_verification_plan(
    ctx: base.Context,
    candidate_atom_id: str,
) -> str:
    """Return the mandatory primary-source verification plan for a Kurate candidate."""

    out = kurate_verification_plan(base._kernel(), candidate_atom_id)
    await base._progress(ctx, "Primary-source verification plan generated")
    return base._json(out)


@_prompt(
    name="research.kurate_triage",
    description="Use Kurate safely as a discovery signal inside Research Kernel.",
)
def prompt_kurate_triage(run_id: str = "", target_atom_id: str = "") -> str:
    return f"""Use Kurate only as a literature-discovery and prioritisation layer.

Run: {run_id}
Target atom: {target_atom_id}

Workflow:
1. Capture a public Kurate paper assessment as a JSON snapshot outside the deterministic kernel.
2. Call rk_kurate_import. Link it to the target only as a discovery analogy.
3. Use rk_kurate_candidates to prioritise what to read.
4. Call rk_kurate_verification_plan for any candidate selected for deeper work.
5. Retrieve and read the primary paper independently.
6. Extract exact source-bound claims into Research Kernel atoms.
7. Attach the primary paper with rk_evidence_attach(source_type='paper').
8. Record disagreements with Kurate instead of silently copying its scores.
9. Run contradiction retrieval and refutation before promotion.

Never use a Kurate score, rank, impact assessment, or tournament result as direct support, refutation, replay evidence, or proof of novelty."""


def _self_test() -> dict[str, Any]:
    base_result = base._self_test()
    return {
        **base_result,
        "kurate_extension": True,
        "kurate_tools": [
            "rk_kurate_import",
            "rk_kurate_candidates",
            "rk_kurate_verification_plan",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Research Kernel MCP server with Kurate discovery extension"
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic backend self-test and exit",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
    )
    parser.add_argument("--mount-path", default=None)
    args = parser.parse_args()

    if args.self_test:
        print(base._json(_self_test()))
        raise SystemExit(0)

    if mcp is None:
        print(
            json.dumps(
                {"ok": False, "error": "mcp_fastmcp_not_installed"},
                sort_keys=True,
            )
        )
        raise SystemExit(1)
    mcp.run(transport=args.transport, mount_path=args.mount_path)
