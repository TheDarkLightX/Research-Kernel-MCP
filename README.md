# Research Kernel MCP

Research Kernel MCP is a durable, evidence-first research substrate for MCP
clients. It stores public research artifacts and avoids hidden reasoning traces.

The model stays creative. The kernel stays deterministic:

- persistent SQLite state;
- append-only event log;
- typed research atoms and graph edges;
- source, artifact, benchmark, proof, and counterexample evidence;
- deterministic Morph-style reformulation templates;
- fail-closed PopperPad-style claim promotion;
- frontier scoring for the next research action;
- MCP tools, resources, and prompts.

## Storage

By default the server writes to:

```text
internal/research_kernel/
```

Override with:

```bash
RESEARCH_HOME=/absolute/path/to/research-vault
```

Artifacts are copied into `RESEARCH_HOME/artifacts` by SHA-256 hash. File
artifacts are accepted only from the repo root, `RESEARCH_HOME`, or paths in
`RK_ARTIFACT_ALLOWLIST` unless `RK_ALLOW_OUTSIDE_ARTIFACTS=1` is set.

Every state-changing operation is also appended to `RESEARCH_HOME/events.jsonl`
for replay and external ledger ingestion.

## Tools

The MCP exposes the compact tool surface from the design spec:

- `rk_start`
- `rk_atom_add`
- `rk_link`
- `rk_retrieve`
- `rk_morph`
- `rk_refute`
- `rk_evidence_attach`
- `rk_score`
- `rk_frontier`
- `rk_promote`
- `rk_report`

`rk_promote` is fail-closed. A claim cannot become `SUPPORTED` unless it has
support evidence, a refutation attempt, dependencies, provenance, contradiction
search, replay evidence when required, and a rationale.

`rk_refute` treats `counterexample` text as planning context unless
`counterexample_is_actual=true` is set. Actual counterexamples create a
`COUNTEREXAMPLE` atom, add a `REFUTES` edge, and mark the target `REFUTED`.

Evidence attached with only a summary can support a claim, but it does not
satisfy promotion provenance. Include `source_uri`, `artifact_path`, or
`artifact_text` on at least one evidence record before promoting a claim.

## Resources

- `rk://runs/{run_id}/summary`
- `rk://runs/{run_id}/graph`
- `rk://runs/{run_id}/frontier`
- `rk://atoms/{atom_id}`
- `rk://claims/{claim_id}`
- `rk://artifacts/{artifact_hash}`
- `rk://memory/similar/{query}`
- `rk://memory/contradictions/{claim_id}`
- `rk://reports/latest`

## Prompts

- `research.kernel_mode`
- `research.start`
- `research.decompose`
- `research.refute`
- `research.morph`
- `research.evidence_review`
- `research.promote_claim`
- `research.report`
- `research.next_frontier`

## Run

Self-test:

```bash
.venv/bin/python internal/research_kernel_mcp/server.py --self-test
```

Stdio MCP:

```bash
uv run --no-project --with mcp python internal/research_kernel_mcp/server.py
```

Streamable HTTP:

```bash
uv run --no-project --with mcp python internal/research_kernel_mcp/server.py \
  --transport streamable-http \
  --mount-path /mcp
```

Focused tests:

```bash
pytest -q tests/internal/test_research_kernel_mcp.py
```

## Boundaries

- The kernel stores research artifacts, evidence, and graph state.
- Hidden chain-of-thought stays outside the artifact store.
- `SUPPORTED` means the local gate passed. External publication or production
  posture still needs the relevant replay, review, and release gates.
- Morph reformulations are candidate search objects until separately tested.

## License

Research Kernel MCP is licensed under the Apache License, Version 2.0. See
the repository root `LICENSE` file.
