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
- `rk_kurate_discover`
- `rk_literature_import`
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

### Kurate discovery adapter

`rk_kurate_discover` performs a bounded, read-only query against Kurate's
paper-ranking feed and stores each result as a `RESULT` atom in `CANDIDATE`
state. The adapter preserves exact arXiv versions, null metrics, a canonical
snapshot hash, and an immutable copy of the response. Scores are stored as
integer milli-points so the discovery receipt is deterministic. The normalized
`research-discovery/candidate/v1` object matches PopperPad's Kurate adapter,
while each system retains its own validation and authority gate.

The authority boundary is deliberate:

- Kurate objects use `authority="triage_only"`;
- evidence uses `source_type="kurate_discovery"` or
  `kurate_discovery_batch`;
- neither source type belongs to the promotion gate's supporting-evidence
  allowlist;
- failed requests and schema drift become `UNKNOWN` negative-knowledge atoms;
- a later assessment for the same arXiv work supersedes the older discovery
  receipt without deleting it.

Example MCP call:

```text
rk_kurate_discover(
  run_id="my-run",
  search="symmetric projection operator",
  categories_json="[\"math.AG\",\"math.NT\"]",
  sort_key="novelty",
  limit=8
)
```

Set `apply_triage_scores=true` only when the run explicitly authorizes Kurate's
novelty, significance, and refutation-value assessments to influence frontier
ordering. Even then, the imported evidence score remains zero. Verify the exact
primary source and attach independent `paper`, `proof`, `experiment`, or test
evidence before attempting claim promotion.

### Citracer and MOSAIC import

`rk_literature_import` consumes an existing provider JSON export. Citracer
imports retain normalized paper nodes and citation relations. MOSAIC imports
retain deduplicated papers and any partial-source errors. The exact JSON bytes
are stored by content hash.

```text
rk_literature_import(
  run_id="my-run",
  provider="citracer",
  artifact_path="research/trace.json"
)
```

The artifact must be inside the repository, `RESEARCH_HOME`, or an explicit
`RK_ARTIFACT_ALLOWLIST` root. Both providers remain `triage_only`. Parsed
citations use a `CITES` graph edge that is excluded from support, refutation,
dependency, and promotion gates. Missing retrieval-policy metadata is recorded
as `unspecified`, not inferred.

Fleet coordinators can use the receipt-bound command adapter. It verifies the
frozen export hash before and after import and writes a
`codex-fleet-literature-import-receipt/v1` file containing stable `rk://`
references:

```bash
python3 internal/research_kernel_mcp/literature_importer.py \
  --home RESEARCH_HOME --run-id fleet-literature \
  --goal "Fleet literature triage" \
  --artifact export.json --artifact-sha256 sha256:... \
  --provider mosaic --receipt receipt.json \
  --import-id mosaic-broad --importer-id research-kernel
```

The receipt remains `triage_only` and does not satisfy a promotion gate.

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
