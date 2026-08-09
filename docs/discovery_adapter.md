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

## Providers in v1

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
1. domain feed / Kurate / Semantic Scholar search
2. normalize candidate records through this adapter
3. reconcile DOI/arXiv/ePrint/DBLP identifiers
4. expand references and citations
5. add QUESTION / HYPOTHESIS / RISK atoms
6. use exact-phrase and contradiction search
7. attach primary papers/proofs/experiments as actual evidence
8. refute important claims
9. only then call rk_promote
```

Kurate scores, citation counts, recommendation rank, and graph centrality are all **priority signals**, not truth signals.

## Failure behavior

The adapter fails visibly on HTTP/network/non-JSON errors and emits no synthetic substitute. It caps result limits to avoid accidental large calls. Provider responses are hashed before normalization so a saved discovery record can retain a provenance fingerprint even though the remote service may later update its metadata.

## Future providers

Good next additions include:

- IACR ePrint / domain-specific feeds;
- DBLP identity resolution;
- OpenAlex once its current authentication/quota contract is configured explicitly;
- Kurate if it exposes a stable machine API suitable for automated use.

Each provider should remain replaceable. No provider-specific score should enter `rk_promote` as evidence.
