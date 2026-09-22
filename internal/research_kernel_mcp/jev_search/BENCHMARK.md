# First live development benchmark — 2026-09-21

The first successfully completed evaluation passed the acceptance criteria fixed
before any usable Jev results were returned. This is a small, authored development
test of an optional reading aid, not a held-out estimate of general search quality.

## Scope and measurements

The operator approved a frozen export of 67 research records, eight questions and
40 requests to the official TypeSafe API. Six questions had designated relevant
records and required context; two concerned topics absent from the corpus.
Queries included paraphrases of research findings, failed ideas and corrections.
Each query scored every record. No research-record text or API credential is
included in this public benchmark summary.

| Frozen check | Observed result |
|---|---|
| At least five of six positive queries find a relevant top-three lead | 6/6 |
| More positive top-three hits than the declared local FTS5 baseline | 6/6 vs 3/6 |
| All designated corrections and failed-result context retained | Passed |
| Both absent-topic queries return no leads | 2/2 |
| Each positive reading packet smaller than the full normalized corpus | Passed; 59–94% fewer serialized bytes |
| Warm replay reproduces the packet without new API calls | Passed; zero calls/tokens |

All 40 requests succeeded with pinned model `jev-1.13.0`. Reported input usage was
149,705 tokens, costing an estimated **$0.006287610** at $0.042/M input tokens.
Whole-query elapsed time was 5.83–6.48 seconds, median 6.17 seconds, with five
sequential API requests per query. The cached replay took about 4 milliseconds.
Returned positive-query JSON totaled 59,263 bytes versus 285,684 bytes for six
copies of the full corpus: a 79.26% aggregate reduction.

## Reproducibility boundaries

The local audit checked all sent request bodies against the exact approved
packet, all raw response hashes, and the frozen input hashes. The export packet
SHA-256 was `73635c4e16289bf3e5ad92b939b08a2ca62c111980a21627846403c277b73515`.
First successful outcomes, packet contents and raw receipts remain in the
operator's local research report; this public summary is not an independently
replayable release of that corpus. The repository tests use invented records.

An earlier sandboxed attempt failed transport on eight calls and produced no
usable semantic answers. Those failures and their conservative unknown-billing
reservations are retained separately. The successful run followed explicit export
approval; questions, labels, prompts and thresholds were not tuned between runs.

The FTS5 comparator used content/tags, at most 16 query tokens and OR matching;
it was not an optimized lexical retrieval system. A top-three hit means at least
one relevant lead, not that all three leads were relevant. Required-context
retention covers the designated records and available graph/ID relationships,
not every possible omitted correction. Byte reduction does not establish savings
in billed frontier-model tokens, latency or total application cost. Accuracy on
other runs, adversarial content and larger corpora remains unmeasured.
