# Kurate discovery signals in Research Kernel MCP

Kurate can improve Research Kernel's literature discovery and prioritisation,
but it must remain outside the scientific evidence gate.

The safe architecture is:

```text
public Kurate assessment
        ↓ external capture
immutable JSON snapshot
        ↓ rk_kurate_import
CANDIDATE literature observation
        ↓ ANALOGIZES only
research claim or open problem
        ↓ human/agent selection
primary-source verification plan
        ↓ independent paper retrieval and reading
source-bound claim atoms
        ↓ rk_evidence_attach(source_type="paper")
ordinary refutation, contradiction, replay, and promotion gates
```

## Why discovery-only

Kurate publishes useful AI-assisted assessment dimensions and rankings. Those
signals can answer questions such as:

```text
Which papers should be read first?
Which paper may contain a strong counterexample or replication opportunity?
Which candidate appears foundational or cross-disciplinary?
Which new paper might overlap a proposed novelty claim?
```

They do not answer:

```text
Did the proof check?
Did the experiment occur as described?
Is the paper actually novel relative to all prior work?
Does the paper support or refute this exact Research Kernel claim?
```

Therefore a Kurate assessment is imported as:

```text
atom type:       OBSERVATION
atom status:     CANDIDATE
evidence score:  0
signal class:    discovery_only
promotion:       ineligible
link to claim:   ANALOGIZES
```

It is never attached as evidence to the target claim.

## Deterministic boundary

Research Kernel deliberately does not browse the network. A client, scheduled
collector, or human captures the public Kurate assessment and supplies an
immutable JSON snapshot. The kernel validates, normalises, hashes, stores, and
ranks that snapshot deterministically.

This separation prevents:

- network drift from changing an old research record;
- a page update from silently changing a score;
- an AI assessment from being mistaken for primary evidence;
- a transient rank from satisfying a promotion requirement;
- unreviewed novelty scores from contaminating a paper claim.

Example snapshot:

```text
examples/kurate-assessment.example.json
```

## MCP server

Run the extension server instead of the base server:

```bash
uv run --no-project --with mcp \
  python internal/research_kernel_mcp/kurate_server.py
```

Streamable HTTP:

```bash
uv run --no-project --with mcp \
  python internal/research_kernel_mcp/kurate_server.py \
  --transport streamable-http \
  --mount-path /mcp
```

The extension contains every base Research Kernel tool plus:

```text
rk_kurate_import
rk_kurate_candidates
rk_kurate_verification_plan
```

It also adds the prompt:

```text
research.kurate_triage
```

## Importing a snapshot

Conceptual MCP call:

```text
rk_kurate_import(
  run_id="sqiprime-honest-prefix-0001",
  snapshot_json=<contents of examples/kurate-assessment.example.json>,
  target_atom_ids_json='["HPPL-Q-KANI-BRIDGE"]'
)
```

The call:

1. validates all known metric values as `1..10` or `null`;
2. preserves the primary-paper URI and Kurate URI separately;
3. content-addresses the complete assessment;
4. computes a deterministic triage score;
5. creates one candidate observation;
6. attaches `source_type="discovery_signal"` to that observation only;
7. adds an `ANALOGIZES` edge to each requested target;
8. returns `eligible_as_claim_support=false`.

## Triage score

The default profile prioritises papers useful to an evidence-first research
program:

```text
rigor                 0.18
novelty               0.14
evidence strength     0.14
refutation value      0.12
foundationality       0.12
significance          0.10
replication value     0.08
surprisingness        0.05
reproducibility       0.04
interdisciplinarity   0.03
```

Weights are normalised over metrics that are actually present. The final score
is:

```text
0.75 × weighted Kurate metric composite
+ 0.25 × run-specific relevance score.
```

This is a reading-order heuristic, not a scientific-quality theorem. A run may
supply its own nonnegative weights in the snapshot and should freeze them before
examining candidate outcomes.

## Selecting papers to verify

List all imported candidates:

```text
rk_kurate_candidates(
  run_id="sqiprime-honest-prefix-0001",
  minimum_triage_score=0.65,
  limit=20
)
```

Restrict the queue to candidates linked to one frontier atom:

```text
rk_kurate_candidates(
  run_id="sqiprime-honest-prefix-0001",
  target_atom_id="HPPL-Q-KANI-BRIDGE"
)
```

For a selected candidate:

```text
rk_kurate_verification_plan(candidate_atom_id="...")
```

The returned plan requires:

1. paper identity and version verification;
2. full primary-paper reading;
3. exact claim and hypothesis extraction;
4. an independent rigor, evidence, novelty, and relevance assessment;
5. recording disagreements with Kurate;
6. attachment of the primary paper to the relevant claim;
7. contradiction retrieval and refutation before promotion.

## Converting discovery into evidence

After independently reading the primary paper, create source-bound atoms for its
actual results and limitations. Attach the paper—not the Kurate assessment—to a
Research Kernel claim:

```text
rk_evidence_attach(
  run_id="...",
  atom_id="the-specific-claim",
  source_type="paper",
  source_uri="the-primary-paper-uri",
  quote="a short exact passage when useful",
  summary="an accurate independent statement of the result and assumptions",
  reliability=<independent assessment>
)
```

Then use the ordinary workflow:

```text
rk_retrieve contradictions and prior failures
rk_refute the claim or proposed use
rk_score
rk_frontier
rk_promote only after every normal gate passes
```

## Recommended use in the isogeny-cryptography program

Use Kurate to maintain several separate reading queues:

```text
novelty overlap:
  refined Humbert invariants, Kani reducibility, theta isogenies,
  formal cryptographic refinement;

refutation radar:
  counterexamples, exceptional loci, sampler failures,
  reducible anti-isometries;

tool transfer:
  arithmetic geometry, moduli spaces, spectral graph theory,
  algorithmic information theory, formal verification;

replication queue:
  computational isogeny claims with code, datasets, or explicit parameters.
```

The categories and query policy belong in each Research Kernel run's
preregistered constraints. Kurate ranks should never change a hypothesis status
by themselves.

## Future automated collector

A later network-facing collector can be added when a stable documented feed or
API is available. It should remain a separate process with this contract:

```text
network collector
  -> capture raw response and timestamp
  -> validate identity and schema
  -> emit immutable snapshot
  -> Research Kernel import
```

The deterministic kernel should not acquire direct network access.

## Assurance tests

The focused tests verify that:

- snapshot normalisation is deterministic;
- invalid metrics fail closed;
- candidate ordering uses the frozen triage formula;
- Kurate creates an `OBSERVATION`, not a claim;
- target claims receive no evidence row;
- links are `ANALOGIZES`, never `SUPPORTS`;
- the target promotion gate remains blocked without primary provenance;
- the verification plan requires the primary paper;
- the extension server launches its deterministic self-test.

Run:

```bash
pytest -q \
  tests/internal/test_research_kernel_mcp.py \
  tests/internal/test_kurate_adapter.py
```
