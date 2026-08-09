# Kurate as a Research Kernel discovery layer

Kurate is useful to Research Kernel, but it belongs **before evidence promotion**.
It is an AI-assisted literature-ranking and assessment service, not a source of
scientific truth.  The safe architecture is therefore:

```text
Kurate discovery
    -> discovery-only candidate atom
    -> Research Kernel frontier ranking
    -> independently fetch primary paper
    -> extract exact claims/hypotheses
    -> attach primary-source evidence
    -> contradiction/refutation search
    -> fail-closed promotion
```

The deterministic Research Kernel remains network-free.  A browser, agent, or
other external adapter captures a public Kurate page/API result and passes the
snapshot to the Kurate MCP extension.  The imported snapshot is content-addressed
and stored for auditability, but it is tagged `discovery_signal` and cannot count
as support evidence for another claim.

## Why it helps

Kurate's multi-dimensional assessment gives the kernel a useful *search prior*:

- novelty -> potentially unexplored directions;
- rigor / evidence strength -> papers worth reading carefully;
- refutation value -> papers likely to generate falsifiable research;
- replication value / reproducibility -> cheap, concrete experiments;
- foundationality / significance -> high-upside theory work;
- interdisciplinarity -> bridge papers that may expose overlooked tools;
- resource intensity / difficulty -> execution-cost context.

These are triage signals only.  Research Kernel still requires primary-source
provenance, refutation attempts, contradiction search, and replay/proof evidence
before a claim can become `SUPPORTED`.

## Run the extended MCP server

Self-test:

```bash
uv run --no-project --with mcp python internal/research_kernel_mcp/kurate_server.py --self-test
```

Stdio MCP:

```bash
uv run --no-project --with mcp python internal/research_kernel_mcp/kurate_server.py
```

Streamable HTTP:

```bash
uv run --no-project --with mcp python internal/research_kernel_mcp/kurate_server.py \
  --transport streamable-http \
  --mount-path /mcp
```

The sidecar imports the ordinary Research Kernel server first, so all existing
`rk_*` tools remain available.  It adds:

- `rk_kurate_import`
- `rk_kurate_candidates`
- `rk_kurate_verification_plan`
- prompt `research.kurate_triage`

## 1. Capture a Kurate snapshot outside the kernel

A snapshot should contain the primary paper URI and the public Kurate assessment.
Example:

```json
{
  "title": "Example paper",
  "identifier": "arXiv:2608.00001v1",
  "primary_uri": "https://arxiv.org/abs/2608.00001",
  "kurate_uri": "https://kurate.org/paper/example",
  "categories": ["cs.CR", "Public-key Cryptography"],
  "captured_at": "2026-08-09T22:00:00Z",
  "assessment_model": "model-name-from-page",
  "prompt_version": "kurate-16-metric",
  "assessment_summary": "Short public assessment summary",
  "metrics": {
    "score": 8.0,
    "significance": 8.0,
    "rigor": 7.0,
    "novelty": 9.0,
    "clarity": 7.0,
    "difficulty": 8.0,
    "surprisingness": 8.0,
    "reproducibility": 6.0,
    "translational_potential": 5.0,
    "evidence_strength": 7.0,
    "generalisability": 7.0,
    "interdisciplinarity": 5.0,
    "refutation_value": 9.0,
    "replication_value": 7.0,
    "resource_intensity": 4.0,
    "foundationality": 8.0
  },
  "reasons": {
    "novelty_reason": "...",
    "refutation_value_reason": "..."
  },
  "ranks": {"cs.CR": 12},
  "relevance_score": 0.95
}
```

Metrics may be `null` when Kurate does not assess a dimension.

## 2. Import it

Call:

```text
rk_kurate_import(
  run_id = <research run>,
  snapshot_json = <JSON above>,
  target_atom_ids_json = [<optional hypotheses/open problems>]
)
```

The tool creates a `CANDIDATE` `OBSERVATION` atom.  It sets:

```text
evidence_score = 0
source_type    = discovery_signal
```

and stores the Kurate snapshot as a content-addressed artifact.  Optional links
to current hypotheses use `ANALOGIZES`, not `SUPPORTS`.

## 3. Let it influence the frontier

Use:

```text
rk_kurate_candidates(run_id, minimum_triage_score=...)
rk_frontier(run_id)
```

Kurate's assessment is converted into a deterministic triage score.  The default
profile emphasizes rigor, novelty, evidence strength, refutation value,
replication value, foundationality, significance, reproducibility, and related
research value.  `relevance_score` is supplied by the Research Kernel client,
not Kurate, so a spectacular but irrelevant paper does not dominate a run.

The score is a *reading priority*, not a confidence in truth.

## 4. Verify the primary paper before evidentiary use

For a selected candidate call:

```text
rk_kurate_verification_plan(candidate_atom_id)
```

The required sequence is:

1. verify paper identity/version;
2. read the primary full text;
3. extract exact source-bound claims and assumptions;
4. assess the work independently and record disagreements with Kurate;
5. attach the primary paper to relevant claims with `source_type="paper"`;
6. retrieve contradictory evidence and try refutation.

Only the primary paper (and subsequent proof/experiment artifacts) can become
claim evidence.

## Recommended Research Kernel policy

### Use Kurate for

- continuous frontier discovery;
- choosing what to read next;
- high-novelty / high-refutation paper hunts;
- replication candidates;
- cross-field tool transfer;
- identifying papers with unusually high foundational or reproducibility value.

### Do not use Kurate for

- proving novelty;
- proving a theorem or experimental result;
- replacing a primary paper;
- satisfying `rk_promote` support evidence;
- assigning truth confidence directly;
- deciding publication worthiness by itself.

## Suggested isogeny-cryptography scan profile

For the IsogenyCryptoExpl run, prioritize recent candidates in cryptography,
public-key cryptography, algebra/number theory, formal methods, and adjacent
quantum/PQC categories.  High-value patterns include:

```text
novelty high + refutation_value high
    -> attack / counterexample candidate

foundationality high + rigor high
    -> theorem dependency / proof-model paper

replication_value high + resource_intensity low
    -> immediate reproduction experiment

interdisciplinarity high + relevance high
    -> possible technique transfer into isogeny cryptanalysis
```

Then convert the selected paper into falsifiable Research Kernel hypotheses,
not a summary-only note.

## Architectural boundary

`ResearchKernel` itself intentionally remains deterministic and network-free.
The Kurate sidecar performs no Kurate scraping either: it accepts a captured
public snapshot from the MCP client.  This avoids depending on undocumented web
endpoints and makes every imported assessment replayable by hash.
