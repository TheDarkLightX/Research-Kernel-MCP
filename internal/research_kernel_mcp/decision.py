"""Deterministic decision support for the research frontier. Pure functions; no storage.

Two exact queries are ported from Zeno-ADP 0.8.0 and checked against vectors it produced
(``tests/internal/vectors/zeno_adp_0_8_0.json``):

* ``common_optimum``: the candidates that are optimal in every selected cost model, for a
  flat set of candidates. This is Zeno-ADP ``common_optimum::common`` on a one-cell chart.
* ``zero_regret`` and ``within_budget``: robust plan prefixes, as in
  ``robust_prefix::{zero_regret, within_budget}``. A plan chart has cells; each rule either
  steps to a cell with a smaller index or finishes, with one cost per world and a
  nonnegative credit. A prefix is a rule sequence from the root. Its regret in a world is
  the sum of the slacks of its rules, which is the extra cost of committing to it and then
  finishing optimally.

The research frontier uses integer milli-point components, Pareto layers, and the common
optimum across declared weightings instead of one hand-weighted float sum. The refutation
plan ranks candidate refutation attempts by how many promotion decisions their outcome
could change, and commits to the attempts that stay optimal in every outcome world.

Nothing here changes a claim's status or relaxes the promotion gate.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import product
from typing import Any

# --- robust plan prefixes (port of zeno_adp::robust_prefix) ---------------------------------


@dataclass(frozen=True)
class Step:
    """A plan rule: one cost per world, a credit for useful work, and a child or None."""

    costs: tuple[int, ...]
    credit: int
    child: int | None = None


class PlanChart:
    """Cells of steps; every child index is smaller than its cell, as in a Zeno-ADP chart."""

    def __init__(self, cells: Sequence[Sequence[Step]], root: int, worlds: int):
        if not 0 <= root < len(cells) or worlds < 1:
            raise ValueError("invalid plan chart root or world count")
        for cell, rules in enumerate(cells):
            for step in rules:
                if len(step.costs) != worlds or step.credit < 0:
                    raise ValueError(f"cell {cell}: each step needs {worlds} costs and a nonnegative credit")
                if step.child is not None and not 0 <= step.child < cell:
                    raise ValueError(f"cell {cell}: a step's child must have a smaller index")
        self.cells = [list(rules) for rules in cells]
        self.root, self.worlds = root, worlds
        self.values = self._values()
        if any(self.values[root][w] is None for w in range(worlds)):
            raise ValueError("some world has no plan from the root")

    def _values(self) -> list[list[int | None]]:
        values: list[list[int | None]] = []
        for rules in self.cells:
            row: list[int | None] = []
            for w in range(self.worlds):
                best = None
                for step in rules:
                    tail = 0 if step.child is None else values[step.child][w]
                    if tail is not None and (best is None or step.costs[w] + tail < best):
                        best = step.costs[w] + tail
                row.append(best)
            values.append(row)
        return values

    def slack(self, cell: int, rule: int, world: int) -> int | None:
        step = self.cells[cell][rule]
        tail = 0 if step.child is None else self.values[step.child][world]
        if tail is None or self.values[cell][world] is None:
            return None
        return step.costs[world] + tail - self.values[cell][world]

    def zero_slack(self, cell: int, rule: int) -> bool:
        return all(self.slack(cell, rule, w) == 0 for w in range(self.worlds))

    def regret(self, rules: Sequence[tuple[int, int]]) -> list[int]:
        total, cell = [0] * self.worlds, self.root
        for at, index in rules:
            if at != cell:
                raise ValueError("rule sequence does not start at the root or skips a cell")
            for w in range(self.worlds):
                s = self.slack(at, index, w)
                if s is None:
                    raise ValueError("rule leads to a cell with no plan")
                total[w] += s
            cell = self.cells[at][index].child
        return total

    def complete(self, start: int | None, world: int) -> list[tuple[int, int]]:
        """The first optimal finish from @p start in one world: zero-slack rules in rule order."""
        plan, cell = [], start
        while cell is not None:
            index = next(i for i in range(len(self.cells[cell])) if self.slack(cell, i, world) == 0)
            plan.append((cell, index))
            cell = self.cells[cell][index].child
        return plan


def zero_regret(chart: PlanChart) -> dict[str, Any]:
    """The prefix of greatest credit whose rules have zero slack in every world."""
    n = len(chart.cells)
    credit, counts, reach = [0] * n, [0] * n, [False] * n
    for cell in range(n):
        best, count = 0, 1  # Stopping is a prefix of credit zero.
        for index, step in enumerate(chart.cells[cell]):
            if not chart.zero_slack(cell, index):
                continue
            value = step.credit + (0 if step.child is None else credit[step.child])
            ways = 1 if step.child is None else counts[step.child]
            if value > best:
                best, count = value, ways
            elif value == best:
                count += ways
            reach[cell] = reach[cell] or step.child is None or reach[step.child]
        credit[cell], counts[cell] = best, count
    prefix, cell = [], chart.root
    while cell is not None and credit[cell] > 0:
        for index, step in enumerate(chart.cells[cell]):
            tail = 0 if step.child is None else credit[step.child]
            if chart.zero_slack(cell, index) and step.credit + tail == credit[cell]:
                prefix.append((cell, index))
                cell = step.child
                break
    end = chart.cells[prefix[-1][0]][prefix[-1][1]].child if prefix else chart.root
    completions = [prefix + chart.complete(end, w) for w in range(chart.worlds)]
    common_plan = None
    if reach[chart.root]:
        common_plan, cell = [], chart.root
        while cell is not None:
            index = next(i for i, step in enumerate(chart.cells[cell]) if chart.zero_slack(cell, i)
                         and (step.child is None or reach[step.child]))
            common_plan.append((cell, index))
            cell = chart.cells[cell][index].child
    return {"best_credit": credit[chart.root], "count": counts[chart.root], "prefix": prefix,
            "common_plan": common_plan, "completions": completions}


def within_budget(chart: PlanChart, budget: Sequence[int]) -> dict[str, Any]:
    """The prefix of greatest credit whose regret is within @p budget in every world."""
    if len(budget) != chart.worlds or any(b < 0 for b in budget):
        raise ValueError("budget needs one nonnegative entry per world")
    memo: dict[tuple[int, tuple[int, ...]], tuple[int, int, list[tuple[int, int]]]] = {}

    def best(cell: int | None, left: tuple[int, ...]) -> tuple[int, int, list[tuple[int, int]]]:
        if cell is None:
            return 0, 1, []
        key = (cell, left)
        if key not in memo:
            top, count, first = 0, 1, []
            for index, step in enumerate(chart.cells[cell]):
                slacks = [chart.slack(cell, index, w) for w in range(chart.worlds)]
                if any(s is None for s in slacks):
                    continue
                rest = tuple(b - s for b, s in zip(left, slacks))
                if any(r < 0 for r in rest):
                    continue
                if step.child is None:
                    value, ways, tail = step.credit, 1, []
                else:
                    sub, ways, tail = best(step.child, rest)
                    value = step.credit + sub
                if value > top:
                    top, count, first = value, ways, [(cell, index)] + tail
                elif value == top:
                    count += ways
            memo[key] = (top, count, first)
        return memo[key]

    top, count, prefix = best(chart.root, tuple(budget))
    return {"best": top, "count": count, "prefix": prefix, "regret": chart.regret(prefix)}


# --- common optimum (port of zeno_adp::common_optimum::common, one cell) -----------------------


def common_optimum(costs: Sequence[Sequence[int]], models: Iterable[int]) -> dict[str, Any]:
    """Candidates whose cost is least in every selected model; the first is the lowest index."""
    selected = sorted(set(models))
    if not costs or not selected:
        raise ValueError("common optimum needs candidates and a nonempty model selection")
    least = {m: min(c[m] for c in costs) for m in selected}
    winners = [i for i, c in enumerate(costs) if all(c[m] == least[m] for m in selected)]
    return {"exists": bool(winners), "count": len(winners), "first": winners[0] if winners else None,
            "winners": winners}


# --- the research frontier --------------------------------------------------------------------

#: Components, all integer milli-points. Higher is better except ``contradiction``.
COMPONENTS = ("importance", "uncertainty", "refutability", "novelty", "lineage", "contradiction")

#: Declared weightings. ``balanced`` reproduces the earlier priority formula exactly.
DEFAULT_MODELS: dict[str, dict[str, int]] = {
    "balanced": {"importance": 1, "uncertainty": 1, "refutability": 1, "novelty": 1, "lineage": 1,
                 "contradiction": -1},
    "refutation": {"importance": 1, "uncertainty": 1, "refutability": 2, "contradiction": -1},
    "exploration": {"importance": 1, "uncertainty": 1, "novelty": 2, "contradiction": -1},
}


def milli(score: float) -> int:
    """A stored score in [0, 1] as integer milli-points, rounded half to even."""
    return round(float(score) * 1000)


def components(atom: dict[str, Any], refute_count: int) -> dict[str, int]:
    return {
        "importance": milli(atom["importance_score"]),
        "uncertainty": milli(atom["uncertainty_score"]),
        "refutability": milli(atom["refutability_score"]),
        "novelty": milli(atom["novelty_score"]),
        "lineage": min(1000, 150 * len(atom["parent_ids"])),
        "contradiction": min(1000, 250 * refute_count),
    }


def dominates(a: dict[str, int], b: dict[str, int]) -> bool:
    """@p a is at least as good as @p b on every component and better on one."""
    keys = COMPONENTS
    better_or_equal = all((a[k] <= b[k]) if k == "contradiction" else (a[k] >= b[k]) for k in keys)
    return better_or_equal and any(a[k] != b[k] for k in keys)


def pareto_layers(items: dict[str, dict[str, int]]) -> dict[str, dict[str, Any]]:
    """Layer 0 is the nondominated set; layer k is nondominated once layers below k are removed.

    Each item also names one item of the previous layer that dominates it, as a witness.
    """
    remaining, layer, out = dict(items), 0, {}
    while remaining:
        front = sorted(i for i in remaining if not any(dominates(remaining[j], remaining[i]) for j in remaining))
        for i in front:
            witness = None
            if layer:
                witness = next(j for j in sorted(out) if out[j]["layer"] == layer - 1 and dominates(items[j], items[i]))
            out[i] = {"layer": layer, "dominated_by": witness}
        for i in front:
            del remaining[i]
        layer += 1
    return out


def parse_models(models: dict[str, dict[str, int]] | None) -> dict[str, dict[str, int]]:
    if models is None:
        return dict(DEFAULT_MODELS)
    if not isinstance(models, dict) or not 1 <= len(models) <= 8:
        raise ValueError("models must map 1 to 8 names to weight objects")
    parsed = {}
    for name, weights in models.items():
        if not isinstance(name, str) or not name or not isinstance(weights, dict) or not weights:
            raise ValueError("each model needs a name and a nonempty weight object")
        for key, weight in weights.items():
            if key not in COMPONENTS or type(weight) is not int or not -10 <= weight <= 10:
                raise ValueError(f"model {name}: weights are integers in -10..10 over {', '.join(COMPONENTS)}")
        parsed[name] = dict(weights)
    return parsed


def model_score(parts: dict[str, int], weights: dict[str, int]) -> int:
    return sum(weight * parts[key] for key, weight in weights.items())


def rank_frontier(items: dict[str, dict[str, int]], models: dict[str, dict[str, int]]) -> dict[str, Any]:
    """Order by Pareto layer, then the balanced score, then ID; report the common optimum."""
    ids = sorted(items)
    layers = pareto_layers(items)
    names = sorted(models)
    costs = [[-model_score(items[i], models[m]) for m in names] for i in ids]
    optimal_in = {i: [m for k, m in enumerate(names) if costs[n][k] == min(c[k] for c in costs)]
                  for n, i in enumerate(ids)} if ids else {}
    common = common_optimum(costs, range(len(names))) if ids else {"exists": False, "count": 0, "winners": []}
    balanced = DEFAULT_MODELS["balanced"]
    order = sorted(ids, key=lambda i: (layers[i]["layer"], -model_score(items[i], balanced), i))
    return {"order": order, "layers": layers, "optimal_in": optimal_in,
            "common_optimum": {"models": names, "exists": common["exists"], "count": common["count"],
                               "atoms": [ids[w] for w in common["winners"]]}}


# --- the refutation plan ----------------------------------------------------------------------


def affected(candidates: Sequence[str], depends_on: dict[str, set[str]], claims: Iterable[str]) -> dict[str, set[str]]:
    """For each claim, the candidates its decision hinges on: itself and every candidate it depends on."""
    closure: dict[str, set[str]] = {}

    def ancestors(atom: str, seen: frozenset[str] = frozenset()) -> set[str]:
        if atom in closure:
            return closure[atom]
        found = set()
        for parent in depends_on.get(atom, ()):
            if parent not in seen:
                found |= {parent} | ancestors(parent, seen | {atom})
        closure[atom] = found
        return found

    pool = set(candidates)
    result = {}
    for claim in claims:
        hinge = ({claim} | ancestors(claim)) & pool
        if hinge:
            result[claim] = hinge
    return result


def refutation_chart(candidates: Sequence[str], hinges: dict[str, set[str]], pending_cost: int) -> tuple[PlanChart, list[frozenset[str]]]:
    """A plan chart over sets of attempted candidates, in every outcome world.

    A world fixes which candidates a refutation would refute. Attempting a candidate costs 1
    and earns credit 1. Finishing costs ``pending_cost`` for every decision still pending: a
    claim is settled once an attempted candidate it hinges on is refuted, or once every
    candidate it hinges on has been attempted.
    """
    k = len(candidates)
    worlds = list(product((False, True), repeat=k))  # True: the refutation finds a counterexample.
    subsets = sorted((frozenset(c for c, bit in zip(candidates, mask) if bit)
                      for mask in product((0, 1), repeat=k)), key=lambda s: (-len(s), sorted(s)))
    index = {s: i for i, s in enumerate(subsets)}

    def pending(attempted: frozenset[str], world: tuple[bool, ...]) -> int:
        refuted = {c for c, r in zip(candidates, world) if r}
        return sum(1 for hinge in hinges.values()
                   if not (hinge & attempted & refuted) and not hinge <= attempted)

    cells = []
    for attempted in subsets:
        rules = [Step(tuple(1 for _ in worlds), 1, index[attempted | {c}]) for c in candidates if c not in attempted]
        rules.append(Step(tuple(pending_cost * pending(attempted, w) for w in worlds), 0))
        cells.append(rules)
    return PlanChart(cells, index[frozenset()], len(worlds)), subsets


def attempts_of(chart: PlanChart, subsets: list[frozenset[str]], rules: Sequence[tuple[int, int]]) -> list[str]:
    names = []
    for cell, rule in rules:
        child = chart.cells[cell][rule].child
        if child is not None:
            names.extend(sorted(subsets[child] - subsets[cell]))
    return names
