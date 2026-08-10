from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "research_strategy_sweep.py"
spec = importlib.util.spec_from_file_location("research_strategy_sweep", MODULE_PATH)
assert spec is not None and spec.loader is not None
strategy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strategy)


def test_default_sweep_is_strategy_only_and_deterministic() -> None:
    target = "Recover a hidden prime-degree kernel line from a compact isogeny evaluator."
    modes = list(strategy.DEFAULT_MODES)
    a = strategy.sweep(target, modes, 8)
    b = strategy.sweep(target, modes, 8)
    assert a == b
    assert a["schema"] == "research_kernel/strategy_sweep/v1"
    assert a["epistemic_role"] == "strategy_only"
    assert a["does_not_support_claims"] is True
    assert len(a["strategies"]) == 8
    assert all(item["must_test"] is True for item in a["strategies"])
    assert all(item["receipt_ref"].startswith("sha256:") for item in a["strategies"])


def test_simpler_case_and_symmetry_are_distinct_reformulations() -> None:
    out = strategy.sweep(
        "Solve Problem 6 for prime degree ell.",
        ["simpler_case", "exploit_symmetry"],
        8,
    )
    assert [x["mode"] for x in out["strategies"]] == ["simpler_case", "exploit_symmetry"]
    assert out["strategies"][0]["relation_to_original"] == "special_case"
    assert out["strategies"][1]["relation_to_original"] == "symmetry_reduction"
    assert out["strategies"][0]["statement"] != out["strategies"][1]["statement"]


def test_unknown_mode_fails_closed() -> None:
    try:
        strategy.sweep("x", ["invent_magic"], 8)
    except ValueError as exc:
        assert "unknown strategy mode" in str(exc)
    else:
        raise AssertionError("unknown strategy must fail closed")


def test_limit_is_bounded() -> None:
    all_modes = list(strategy.STRATEGIES)
    out = strategy.sweep("x", all_modes, 3)
    assert len(out["strategies"]) == 3
