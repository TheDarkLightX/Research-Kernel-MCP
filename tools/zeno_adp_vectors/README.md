# Zeno-ADP cross-check vectors

`internal/research_kernel_mcp/decision.py` ports two exact queries from
[Zeno-ADP](https://github.com/TheDarkLightX/Zeno-ADP) 0.8.0 to standard-library Python:
robust plan prefixes (`robust_prefix::zero_regret` and `within_budget`) and common optima
(`common_optimum::common`, on one-cell charts). This directory holds the Rust program that
asks Zeno-ADP itself for the answers. `tests/internal/test_decision.py` requires the Python
ports to match every answer exactly.

The vectors contain:
- 120 seeded random plan charts, up to 8 cells and 4 worlds;
- the 16 refutation charts that `decision.refutation_chart` builds for seeded dependency
  graphs, up to 16 outcome worlds;
- 80 flat cost sets, each with two model selections.

Rebuild or check them (needs a Rust toolchain; the first build fetches the `v0.8.0` tag):

```sh
python3 tools/zeno_adp_vectors/regenerate.py --check
python3 tools/zeno_adp_vectors/regenerate.py --zeno-adp-path ../Zeno-ADP   # a local v0.8.0 checkout
```

The Python package does not depend on Rust or Zeno-ADP at runtime.
