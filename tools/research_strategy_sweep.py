#!/usr/bin/env python3
"""Deterministic problem-solving strategy sweep for Research Kernel MCP.

This companion tool turns general mathematical problem-solving heuristics into
explicit, auditable candidate reformulations.  It does not prove anything and
has no claim authority.  The output is intended to be reviewed and, when
useful, stored as REFORMULATION / QUESTION / RISK atoms before evidence and
refutation work begins.

The strategy vocabulary is inspired in part by Terence Tao's expository post
"245A: Problem solving strategies" (2010), but the templates below are adapted
for a general evidence-first research workflow rather than copied from the
post.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any

SCHEMA = "research_kernel/strategy_sweep/v1"
SOURCE_URI = "https://terrytao.wordpress.com/2010/10/21/245a-problem-solving-strategies/"


STRATEGIES: dict[str, dict[str, str]] = {
    "split_goal": {
        "title": "Split the goal",
        "statement": "Replace a hard equality/equivalence by its two directions, or split a composite conclusion into independently falsifiable obligations: {target}",
        "relation": "decomposition",
    },
    "approximate_first": {
        "title": "Allow controlled slack",
        "statement": "Ask whether an approximate / epsilon / bounded-error version is easier, then identify what limiting or amplification step would recover the exact target: {target}",
        "relation": "weaker",
    },
    "simpler_case": {
        "title": "Keep the difficulty, remove distractions",
        "statement": "Choose the simplest nontrivial special case that preserves the suspected hard mechanism; solve or refute that case before restoring generality: {target}",
        "relation": "special_case",
    },
    "localize": {
        "title": "Work locally",
        "statement": "Replace the global problem by the sharpest local / prime-power / neighborhood / component problem whose solutions can later be patched: {target}",
        "relation": "local_model",
    },
    "exceptional_set": {
        "title": "Separate exceptional strata",
        "statement": "Identify a small or structurally exceptional subset on which the target may fail; solve the generic stratum and quantify the exceptional one separately: {target}",
        "relation": "stratification",
    },
    "counterexample_picture": {
        "title": "Build the smallest counterexample",
        "statement": "Hold the hypotheses fixed and deliberately try to make the conclusion false in the smallest exact model; record exactly which obstruction prevents the counterexample: {target}",
        "relation": "refutation",
    },
    "abstract_irrelevant": {
        "title": "Forget suspected irrelevant structure",
        "statement": "Strip away domain-specific structure until only the information used by the hypothesis and desired conclusion remains; test whether the abstracted statement is true: {target}",
        "relation": "abstraction",
    },
    "expand_definitions": {
        "title": "Expand definitions",
        "statement": "Write the hypothesis and conclusion entirely in primitive definitions and compare them term-by-term before importing higher-level theory: {target}",
        "relation": "equivalent_candidate",
    },
    "exploit_symmetry": {
        "title": "Spend symmetry deliberately",
        "statement": "List the exact symmetries preserving the target, choose useful normalizations, and quotient by redundant representatives before searching: {target}",
        "relation": "symmetry_reduction",
    },
    "linearize": {
        "title": "Linearize around a structured point",
        "statement": "Introduce a small deformation / perturbation parameter, extract first- or second-order necessary conditions, and test whether they reveal the governing invariant: {target}",
        "relation": "necessary_condition",
    },
    "interchange_operations": {
        "title": "Change the order of aggregation",
        "statement": "If the target contains nested sums, products, traces, expectations, searches, or quantifiers, exchange or aggregate them in the other order and look for a compressed invariant: {target}",
        "relation": "reorganization",
    },
    "average_vs_pointwise": {
        "title": "Convert pointwise and average information",
        "statement": "Ask whether pointwise control can be replaced by an average/moment/trace condition (or conversely after discarding a controlled bad set): {target}",
        "relation": "reformulation",
    },
    "generators_and_closure": {
        "title": "Prove generators plus closure",
        "statement": "Find a small generating family of objects/operations, prove the desired property on generators, and prove it is preserved under composition/closure: {target}",
        "relation": "inductive_structure",
    },
    "parameter_later": {
        "title": "Delay parameter optimization",
        "statement": "Keep free parameters symbolic, accumulate all required inequalities/constraints, and optimize only after the full dependency graph is visible: {target}",
        "relation": "optimization_strategy",
    },
}

DEFAULT_MODES = (
    "counterexample_picture",
    "simpler_case",
    "abstract_irrelevant",
    "expand_definitions",
    "exploit_symmetry",
    "localize",
    "interchange_operations",
    "generators_and_closure",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sweep(target: str, modes: list[str], limit: int) -> dict[str, Any]:
    target = target.strip()
    if not target:
        raise ValueError("target is required")
    limit = max(1, min(32, int(limit)))

    items: list[dict[str, Any]] = []
    for mode in modes:
        key = mode.strip().lower()
        if not key:
            continue
        strategy = STRATEGIES.get(key)
        if strategy is None:
            raise ValueError(f"unknown strategy mode: {key}")
        statement = strategy["statement"].format(target=target)
        receipt = hashlib.sha256(
            canonical_json({"target": target, "mode": key, "statement": statement}).encode("utf-8")
        ).hexdigest()
        items.append(
            {
                "id": f"S{len(items)+1}",
                "mode": key,
                "title": strategy["title"],
                "statement": statement,
                "relation_to_original": strategy["relation"],
                "epistemic_role": "strategy_only",
                "must_test": True,
                "receipt_ref": "sha256:" + receipt,
                "next_actions": [
                    "retrieve prior failures and nearby literature",
                    "instantiate the reformulation in the smallest exact model",
                    "try to falsify it before treating it as useful",
                    "attach primary evidence only after the reformulation survives testing",
                ],
            }
        )
        if len(items) >= limit:
            break

    return {
        "schema": SCHEMA,
        "source_uri": SOURCE_URI,
        "target": target,
        "epistemic_role": "strategy_only",
        "does_not_support_claims": True,
        "strategies": items,
        "non_claims": [
            "A strategy suggestion is not evidence that the target is true or important.",
            "A successful special case is not automatically a proof of the general case.",
            "Abstraction can discard decisive structure; every abstraction must be tested against the original problem.",
        ],
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("target")
    p.add_argument("--mode", action="append", default=[], choices=sorted(STRATEGIES))
    p.add_argument("--limit", type=int, default=8)
    p.add_argument("--list-modes", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.list_modes:
        print(json.dumps({k: v["title"] for k, v in STRATEGIES.items()}, sort_keys=True, indent=2))
        return 0
    modes = args.mode or list(DEFAULT_MODES)
    try:
        out = sweep(args.target, modes, args.limit)
    except ValueError as exc:
        print(canonical_json({"ok": False, "error": str(exc)}))
        return 2
    print(json.dumps(out, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
