"""Rebuild tests/internal/vectors/zeno_adp_0_8_0.json from Zeno-ADP 0.8.0.

    python3 tools/zeno_adp_vectors/regenerate.py [--zeno-adp-path PATH] [--check]

Runs this directory's Rust program twice: once for its seeded random plan charts and
one-cell cost sets, and once on the refutation charts that decision.refutation_chart
builds for sixteen seeded dependency graphs. --zeno-adp-path builds against a local
checkout of the v0.8.0 tag instead of fetching it. --check compares with the committed file.
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TARGET = ROOT / "tests" / "internal" / "vectors" / "zeno_adp_0_8_0.json"
sys.path.insert(0, str(ROOT))

from internal.research_kernel_mcp import decision as d  # noqa: E402


def refutation_charts() -> str:
    rnd = random.Random(2026)
    lines = []
    for case in range(16):
        k = 2 + case % 3
        cands = [f"c{i}" for i in range(k)]
        claims = cands + [f"d{i}" for i in range(rnd.randint(0, 4))]
        deps = {c: {rnd.choice(cands)} for c in claims if c.startswith("d")}
        for c in cands[1:]:
            if rnd.random() < 0.4:
                deps.setdefault(c, set()).add(rnd.choice(cands[: cands.index(c)]))
        chart, _ = d.refutation_chart(cands, d.affected(cands, deps, claims), pending_cost=2 + case % 2)
        out = [chart.worlds, chart.root, len(chart.cells)]
        for rules in chart.cells:
            out.append(len(rules))
            for step in rules:
                out += [step.credit, -1 if step.child is None else step.child, *step.costs]
        out += [1 + case % 2] * chart.worlds
        lines.append(" ".join(map(str, out)))
    return "\n".join(lines) + "\n"


def cargo(args: list[str], path: str | None, stdin: str | None = None) -> str:
    command = ["cargo", "run", "--quiet", "--release", "--manifest-path", str(HERE / "Cargo.toml")]
    if path:
        command += ["--config", f'patch."https://github.com/TheDarkLightX/Zeno-ADP".zeno-adp.path="{path}"']
    command += ["--", *args] if args else []
    return subprocess.run(command, input=stdin, capture_output=True, text=True, check=True).stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zeno-adp-path")
    parser.add_argument("--check", action="store_true")
    a = parser.parse_args()
    vectors = json.loads(cargo([], a.zeno_adp_path))
    vectors["refutation_charts"] = json.loads(cargo(["--stdin"], a.zeno_adp_path, refutation_charts()))
    vectors["generator"] = "tools/zeno_adp_vectors (Zeno-ADP 0.8.0, tag v0.8.0, commit b4003a1)"
    text = json.dumps(vectors, separators=(",", ":"))
    if a.check:
        same = TARGET.read_text(encoding="utf-8") == text
        print("vectors match" if same else "vectors differ")
        return 0 if same else 1
    TARGET.write_text(text, encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
