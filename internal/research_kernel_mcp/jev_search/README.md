# Optional Jev semantic search

`rk_semantic_search` provides a reading aid for one bounded research run. It does
not change atoms, edges, evidence scores, promotion checks or existing retrieval.
The core kernel remains deterministic; this explicit optional adapter uses a
probabilistic external service to order a reading packet.

The first approved live development evaluation passed all frozen checks on 67
records and eight questions. See [the measured results and limits](BENCHMARK.md).

## Modes

```text
rk_semantic_search(run_id="my-run", query="What earlier failures apply here?")
rk_semantic_search(run_id="my-run", query="What earlier failures apply here?", mode="live")
rk_semantic_search(run_id="my-run", query="What earlier failures apply here?", mode="cached")
```

Preview is default. It writes an exact local export packet and reports its hash,
scope, candidate count and request budget without loading a credential or calling
the network. `anchor_ids_json='["claim-id"]'` retains a known claim and its linked
context regardless of relevance scores.

Live mode requires both a deliberate tool call and the exact run ID in the
server environment's comma-separated `RK_JEV_ALLOWED_RUNS`. No wildcard is
interpreted. Review the preview for confidential text before enabling a run.
Set `TYPESAFE_API_KEY` server-side or use the owner-only literal key file
`~/.config/secrets/typesafe.env`. Keys never enter research packets or tool args.
Provider: `https://api.typesafe.ai/v1/systemone`, pinned model `jev-1.13.0`.

Cached mode is offline and fails on any missing or invalid cache entry. Results
and usage receipts live under `RESEARCH_HOME/jev-search/<run-id-hash>/`. Nothing
is attached as supporting evidence or recorded as a successful contradiction
search for promotion purposes.

## Retrieval contract

The adapter scores all atoms in a frozen run snapshot with Jev Noul judgments.
There is no keyword prefilter. It includes top-ranked leads above the fixed 0.5
retrieval threshold, then follows evidence, refutation, correction and dependency
links in both directions to fixed point. Exact ID mentions in explicit correction
records also add context links. Status/text remain source facts, not Jev labels.
Full source/artifact references and content hashes remain in the reading packet;
only query/ID/text/type/status/tags go to the API. Artifact files are never opened.

The threshold is not a calibrated probability of correctness. An empty lead list
does not prove relevant evidence is absent. Semantic mistakes, missing graph links
and unnamed corrections can still omit important evidence. Explicit anchors help
when testing a known claim; this adapter cannot establish proof or an edge.

Successful validated responses are cached by exact request content, prompt
version and model. Changes to text invalidate affected batches; graph/provenance
changes recompose the reading packet. Cache integrity checks detect accidental
corruption, not an adversary who rewrites data and every hash. Protect the local
cache like other private process data.

## Limits and failure behavior

- 512 records/run, 16 records and 16 KiB wire/request, 64 KiB compact output.
- Per-run local client allowance: 128 calls and $0.25 estimated cost; fixed
  context-price reservation before each request. Concurrent calls share a ledger.
- Full-query budget preflight; a concurrent consumer can still exhaust the budget
  before later batches. Partial failures return errors, with earlier receipts
  retained. No hidden retries, keyword fallback or successful partial packet.
- Transport failures retain conservative cost reservations. Reported token-based
  estimates use $0.042/M input tokens, output free, checked 2026-09-21; they are
  not invoices or guarantees against price changes.
- The operation is a bounded linear scan, not a vector index or a solution for
  million-record global search. Scope runs and reuse cache; evaluate any later
  shortlist/index stage for recall before introducing it.

Original standard-library implementation based on TypeSafe's
[API](https://docs.typesafe.ai/api), [models](https://docs.typesafe.ai/models) and
[reranking guide](https://docs.typesafe.ai/cookbooks/rerank_typesafe). No community
Jev application code or downloaded embedding model is used.
