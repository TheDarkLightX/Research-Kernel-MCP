from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "research_discovery_adapter.py"
spec = importlib.util.spec_from_file_location("research_discovery_adapter", MODULE_PATH)
assert spec is not None and spec.loader is not None
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def test_semantic_scholar_normalization() -> None:
    item = {
        "paperId": "abc",
        "corpusId": 42,
        "title": " A Paper ",
        "publicationDate": "2026-08-09",
        "venue": "IACR",
        "url": "https://example.test/paper",
        "abstract": "text",
        "citationCount": 7,
        "referenceCount": 11,
        "externalIds": {"DOI": "10.1/x", "ArXiv": "2608.00001", "DBLP": "conf/x/y"},
        "authors": [{"name": "Ada A"}, {"name": "Bob B"}],
    }
    out = adapter.normalize_semantic_scholar(item)
    assert out["provider_record_id"] == "abc"
    assert out["canonical_ids"]["doi"] == "10.1/x"
    assert out["canonical_ids"]["arxiv"] == "2608.00001"
    assert out["authors"] == ["Ada A", "Bob B"]
    assert out["citation_count"] == 7


def test_crossref_normalization_prefers_print_date() -> None:
    item = {
        "DOI": "10.2/y",
        "title": ["Title"],
        "author": [{"given": "Ada", "family": "Lovelace"}],
        "published-print": {"date-parts": [[2026, 7, 2]]},
        "published-online": {"date-parts": [[2026, 6, 1]]},
        "container-title": ["Journal"],
        "URL": "https://doi.org/10.2/y",
        "type": "journal-article",
        "is-referenced-by-count": 5,
        "reference": [{}, {}],
    }
    out = adapter.normalize_crossref(item)
    assert out["canonical_ids"] == {"doi": "10.2/y"}
    assert out["authors"] == ["Ada Lovelace"]
    assert out["publication_date"] == "2026-07-02"
    assert out["reference_count"] == 2


def test_opencitations_metadata_identifiers() -> None:
    item = {
        "id": "doi:10.3/z arxiv:2608.12345 pmid:99",
        "title": "Paper",
        "author": "A; B",
        "pub_date": "2026",
        "venue": "Venue",
        "type": "journal article",
    }
    out = adapter.normalize_opencitations_meta(item)
    assert out["canonical_ids"]["doi"] == "10.3/z"
    assert out["canonical_ids"]["arxiv"] == "2608.12345"
    assert out["authors"] == ["A", "B"]


def test_discovery_signal_is_triage_only_and_hashed() -> None:
    raw = b'{"x":1}'
    signal = adapter.make_signal(
        provider="test",
        operation="search",
        query="q",
        raw=raw,
        items=[{"title": "x"}],
    )
    assert signal["schema"] == "research_kernel/discovery_signal/v1"
    assert signal["source_type"] == "discovery_signal"
    assert signal["epistemic_role"] == "triage_only"
    assert signal["raw_metadata_hash"].startswith("sha256:")
    assert signal["item_count"] == 1


def test_limit_is_fail_safe() -> None:
    assert adapter._limit(0) == 1
    assert adapter._limit(10) == 10
    assert adapter._limit(1000) == adapter.MAX_LIMIT
