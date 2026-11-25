from __future__ import annotations

import json
from pathlib import Path

import pytest

from internal.research_kernel_mcp import decision as d
from internal.research_kernel_mcp.kernel import ResearchKernel

VECTORS = json.loads((Path(__file__).parent / "vectors" / "zeno_adp_0_8_0.json").read_text(encoding="utf-8"))


def _chart(case: dict) -> d.PlanChart:
    cells = [[d.Step(tuple(r["costs"]), r["credit"], r["child"]) for r in rules] for rules in case["cells"]]
    return d.PlanChart(cells, case["root"], case["worlds"])


def _pairs(rules):
    return None if rules is None else [list(p) for p in rules]


@pytest.mark.parametrize("case", VECTORS["robust_prefix"] + VECTORS["refutation_charts"], ids=lambda c: str(c["case"]))
def test_robust_prefix_matches_zeno_adp(case: dict) -> None:
    chart = _chart(case)
    zero, expected = d.zero_regret(chart), case["zero_regret"]
    assert zero["best_credit"] == expected["best_credit"]
    assert str(zero["count"]) == expected["count"]
    assert _pairs(zero["prefix"]) == expected["prefix"]
    assert _pairs(zero["common_plan"]) == expected["common_plan"]
    assert [_pairs(c) for c in zero["completions"]] == expected["completions"]
    within, expected = d.within_budget(chart, case["budget"]), case["within_budget"]
    assert (within["best"], str(within["count"])) == (expected["best"], expected["count"])
    assert _pairs(within["prefix"]) == expected["prefix"]
    assert within["regret"] == expected["regret"]


@pytest.mark.parametrize("case", VECTORS["common_optimum"], ids=lambda c: str(c["case"]))
def test_common_optimum_matches_zeno_adp(case: dict) -> None:
    for answer in case["answers"]:
        got = d.common_optimum(case["costs"], answer["models"])
        assert (got["exists"], str(got["count"]), got["first"]) == (answer["exists"], answer["count"], answer["first"])


def test_vectors_exercise_ties_budgets_and_missing_common_plans() -> None:
    plans = VECTORS["robust_prefix"] + VECTORS["refutation_charts"]
    assert sum(int(c["zero_regret"]["count"]) > 1 for c in plans) >= 10
    assert sum(c["zero_regret"]["common_plan"] is None for c in plans) >= 10
    assert sum(c["within_budget"]["best"] > c["zero_regret"]["best_credit"] for c in plans) >= 10
    assert max(c["worlds"] for c in plans) == 16


def test_plan_chart_rejects_malformed_charts() -> None:
    with pytest.raises(ValueError):
        d.PlanChart([[d.Step((1,), 0, 0)]], 0, 1)  # a child must have a smaller index
    with pytest.raises(ValueError):
        d.PlanChart([[d.Step((1, 2), 0)]], 0, 1)  # one cost per world
    with pytest.raises(ValueError):
        d.PlanChart([[d.Step((1,), -1)]], 0, 1)  # nonnegative credit
    with pytest.raises(ValueError):
        d.PlanChart([[]], 0, 1)  # no plan from the root
    chart = d.PlanChart([[d.Step((0,), 1)]], 0, 1)
    with pytest.raises(ValueError):
        d.within_budget(chart, [-1])


def test_pareto_layers_minimize_contradiction_and_name_a_witness() -> None:
    base = dict.fromkeys(d.COMPONENTS, 500)
    items = {"a": base | {"importance": 900}, "b": base, "c": base | {"contradiction": 750}, "d": base | {"novelty": 900}}
    layers = d.pareto_layers(items)
    assert {k for k, v in layers.items() if v["layer"] == 0} == {"a", "d"}
    assert layers["b"] == {"layer": 1, "dominated_by": "a"}
    assert layers["c"]["layer"] == 2 and layers["c"]["dominated_by"] == "b"


def test_balanced_model_reproduces_the_earlier_priority_formula() -> None:
    atom = {"importance_score": 0.9, "uncertainty_score": 0.8, "refutability_score": 0.9, "novelty_score": 0.5,
            "parent_ids": ["p"]}
    parts = d.components(atom, refute_count=1)
    legacy = 0.9 + 0.8 + 0.9 + 0.5 + min(1.0, 0.15) - min(1.0, 0.25)
    assert d.model_score(parts, d.DEFAULT_MODELS["balanced"]) / 1000 == pytest.approx(legacy, abs=1e-9)


def test_models_are_bounded_integer_weightings() -> None:
    assert d.parse_models({"impact": {"importance": 3}}) == {"impact": {"importance": 3}}
    for bad in [{}, {"x": {}}, {"x": {"luck": 1}}, {"x": {"importance": 1.5}}, {"x": {"importance": 11}},
                {f"m{i}": {"importance": 1} for i in range(9)}]:
        with pytest.raises(ValueError):
            d.parse_models(bad)


def test_common_optimum_across_declared_weightings() -> None:
    base = dict.fromkeys(d.COMPONENTS, 0)
    items = {"x": base | {"importance": 900, "novelty": 900}, "y": base | {"importance": 900}, "z": base | {"novelty": 900}}
    ranked = d.rank_frontier(items, {"impact": {"importance": 1}, "explore": {"novelty": 1}})
    assert ranked["common_optimum"]["atoms"] == ["x"]
    assert ranked["optimal_in"]["y"] == ["impact"]
    assert ranked["order"][0] == "x"


def _claim(kernel: ResearchKernel, run_id: str, text: str, parents: list[str], importance: float) -> str:
    return kernel.atom_add(run_id=run_id, atom_type="CLAIM", content=text, status="CANDIDATE",
                           parent_ids=parents, importance_score=importance)["atom"]["id"]


def _ready(kernel: ResearchKernel, run_id: str, atom_id: str, tmp_path: Path) -> None:
    """Everything the SUPPORTED gate needs except a refutation attempt."""
    kernel.evidence_attach(run_id=run_id, atom_id=atom_id, source_type="benchmark", source_uri="file://bench.log",
                           summary="replay passed", artifact_text="replay passed\n")
    kernel.evidence_attach(run_id=run_id, atom_id=atom_id, source_type="contradiction_search",
                           source_uri="rk://memory/contradictions", summary="none found")


def test_frontier_reports_layers_components_and_common_optimum(tmp_path: Path) -> None:
    kernel = ResearchKernel(tmp_path)
    run_id = kernel.start_run(goal="g", title="t", domain="d", success_criteria="s")["run"]["id"]
    strong = _claim(kernel, run_id, "strong", [], 0.9)
    _claim(kernel, run_id, "weak", [], 0.2)
    out = kernel.frontier(run_id=run_id, limit=5)
    first = out["frontier"][0]
    assert first["atom_id"] == strong and first["pareto_layer"] == 0
    assert out["frontier"][1]["dominated_by"] == strong
    assert first["components"]["importance"] == 900
    assert out["common_optimum"]["atoms"] == [strong]
    assert set(out["models"]) == {"balanced", "refutation", "exploration"}


def test_refutation_plan_ranks_shared_dependencies_and_commits_robustly(tmp_path: Path) -> None:
    kernel = ResearchKernel(tmp_path)
    run_id = kernel.start_run(goal="g", title="t", domain="d", success_criteria="s")["run"]["id"]
    base = _claim(kernel, run_id, "base lemma", [], 0.9)
    left = _claim(kernel, run_id, "left result", [base], 0.6)
    right = _claim(kernel, run_id, "right result", [base], 0.5)
    for atom in (left, right):
        _ready(kernel, run_id, atom, tmp_path)
    plan = kernel.refutation_plan(run_id=run_id, candidates=3, regret_budget=1, pending_cost=3)
    top = plan["ranking"][0]
    assert top["atom_id"] == base
    assert top["decisions_hinging"] == 3
    assert top["promotions_at_stake"] == 2  # Both results are one surviving attempt from SUPPORTED.
    robust = plan["robust"]
    assert robust["worlds"] == 8
    # Refuting the base settles all three decisions at once; otherwise all three must be tried.
    # Attempting the base first is optimal whatever the outcomes, and nothing after it is.
    assert robust["commit_now"] == [base]
    assert robust["one_plan_optimal_in_every_world"] is False
    assert robust["within_budget"]["max_regret"] <= 1
    assert kernel.get_atom(base)["status"] == "CANDIDATE"  # Advisory: no state changes.


def test_refutation_plan_commit_now_has_zero_regret_in_every_world() -> None:
    candidates = ["a", "b", "c"]
    hinges = d.affected(candidates, {"b": {"a"}, "x": {"b"}}, ["a", "b", "c", "x"])
    assert hinges == {"a": {"a"}, "b": {"a", "b"}, "c": {"c"}, "x": {"a", "b"}}
    chart, subsets = d.refutation_chart(candidates, hinges, pending_cost=3)
    zero = d.zero_regret(chart)
    assert all(r == 0 for r in chart.regret(zero["prefix"]))
    within = d.within_budget(chart, [2] * chart.worlds)
    assert max(chart.regret(within["prefix"])) <= 2
    assert len(d.attempts_of(chart, subsets, within["prefix"])) >= len(d.attempts_of(chart, subsets, zero["prefix"]))


def test_refutation_plan_with_no_open_claims_is_empty(tmp_path: Path) -> None:
    kernel = ResearchKernel(tmp_path)
    run_id = kernel.start_run(goal="g", title="t", domain="d", success_criteria="s")["run"]["id"]
    assert kernel.refutation_plan(run_id=run_id)["candidates"] == []
