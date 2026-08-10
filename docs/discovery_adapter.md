# Client-side scholarly discovery adapter

`tools/research_discovery_adapter.py` adds a deliberately **non-authoritative** discovery layer around Research Kernel MCP.

The architectural rule is:

```text
external services decide what deserves attention
Research Kernel decides what deserves belief
```

The deterministic `ResearchKernel` class remains network-free. The adapter performs external retrieval and emits normalized JSON with:

```text
schema = research_kernel/discovery_signal/v1
source_type = discovery_signal
epistemic_role = triage_only
raw_metadata_hash = sha256:...
```

A client may store that record in atom metadata or attach it for provenance, but `discovery_signal` must never satisfy a `SUPPORTED` promotion gate by itself.

## Domain-first rule for cryptography

For cryptography, query the **IACR Cryptology ePrint Archive before broad scholarly indexes**. Same-week preprints, revisions, withdrawals, and attacks can matter before citation/recommendation systems have indexed them.

`tools/iacr_eprint_discovery.py` is a companion adapter for the archive's OAI-PMH metadata interface. It emits the same triage-only discovery schema.

Fetch one paper by canonical ePrint identifier:

```bash
python tools/iacr_eprint_discovery.py paper 2026/1575
```

List a bounded date window:

```bash
python tools/iacr_eprint_discovery.py recent \
  --from-date 2026-08-01 \
  --until-date 2026-08-09 \
  --limit 50
```

The default OAI base is:

```text
https://eprint.iacr.org/oai
```

and may be overridden with `--base-url` if the archive changes its machine endpoint. The parser supports OAI resumption tokens and hashes the concatenated raw XML pages before normalization.

IACR metadata is a **domain discovery/provenance source**, not proof that a preprint's theorem is correct. ePrint papers may be revised or withdrawn and are not necessarily peer reviewed.

## General providers in v1

### Semantic Scholar

```bash
python tools/research_discovery_adapter.py \
  s2-search "isogeny cryptography PRISM" --limit 10
```

Recommendations can combine positive and negative paper seeds:

```bash
python tools/research_discovery_adapter.py \
  s2-recommend \
  --positive 'DOI:10.1000/example' \
  --positive 'ArXiv:2603.00001' \
  --negative 'ArXiv:2501.00002' \
  --limit 20
```

If available, set:

```bash
SEMANTIC_SCHOLAR_API_KEY=...
```

The adapter also works against endpoints that permit shared unauthenticated access; callers must still respect the provider's current rate limits and terms.

### Crossref

```bash
RK_DISCOVERY_CONTACT=research@example.org \
python tools/research_discovery_adapter.py \
  crossref-search "response fiber isogeny signature" --limit 10
```

`RK_DISCOVERY_CONTACT` is sent as Crossref's `mailto` parameter when it looks like an email address and is also used in the User-Agent.

### OpenCitations

Metadata lookup:

```bash
python tools/research_discovery_adapter.py oc-meta 'doi:10.1000/example'
```

Reference/citation edges:

```bash
python tools/research_discovery_adapter.py \
  oc-edges 'doi:10.1000/example' --direction references
```

An OpenCitations token is optional but encouraged by the provider:

```bash
OPENCITATIONS_TOKEN=...
```

## Suggested Research Kernel workflow

```text
1. domain feed (IACR ePrint for cryptography)
2. Kurate / Semantic Scholar / broad discovery
3. normalize candidate records as discovery_signal
4. reconcile DOI/arXiv/ePrint/DBLP identifiers
5. expand references and citations
6. add QUESTION / HYPOTHESIS / RISK atoms
7. use exact-phrase and contradiction search
8. attach primary papers/proofs/experiments as actual evidence
9. refute important claims
10. only then call rk_promote
```

Kurate scores, citation counts, recommendation rank, graph centrality, and ePrint recency are all **priority signals**, not truth signals.

## Failure behavior

The adapters fail visibly on HTTP/network/parse errors and emit no synthetic substitute. They cap result limits to avoid accidental large calls. Provider responses are hashed before normalization so a saved discovery record can retain a provenance fingerprint even though the remote service may later update its metadata.

## Future providers

Good next additions include:

- DBLP identity resolution;
- OpenAlex once its current authentication/quota contract is configured explicitly;
- Kurate if it exposes a stable machine API suitable for automated use;
- optional revision/withdrawal-specific IACR alerts once the exact archive event feed is source-bound and tested.

Each provider should remain replaceable. No provider-specific score should enter `rk_promote` as evidence.
