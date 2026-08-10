#!/usr/bin/env python3
"""Client-side scholarly discovery adapter for Research Kernel MCP.

This module intentionally lives outside the deterministic ResearchKernel class.
It performs network retrieval, normalizes public metadata into auditable
``discovery_signal`` records, and prints JSON for an MCP client/agent to attach
as triage metadata.  A discovery signal is never promotion evidence by itself.

Providers in v1:
- Semantic Scholar Academic Graph search and Recommendations
- Crossref REST bibliographic search
- OpenCitations Meta and Index v2 lookup

Only Python's standard library is required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

SCHEMA = "research_kernel/discovery_signal/v1"
DEFAULT_TIMEOUT = 30.0
DEFAULT_LIMIT = 10
MAX_LIMIT = 100

S2_GRAPH = "https://api.semanticscholar.org/graph/v1"
S2_RECOMMEND = "https://api.semanticscholar.org/recommendations/v1"
CROSSREF = "https://api.crossref.org"
OC_META = "https://api.opencitations.net/meta/v1"
OC_INDEX = "https://api.opencitations.net/index/v2"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_ref(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return [_clean(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    return value


def _first(value: Any, default: str = "") -> str:
    if isinstance(value, list) and value:
        return str(value[0] or default)
    if value is None:
        return default
    return str(value)


def _date_parts(value: Any) -> str:
    """Normalize Crossref date-parts to YYYY[-MM[-DD]]."""
    try:
        parts = value["date-parts"][0]
    except (KeyError, IndexError, TypeError):
        return ""
    if not parts:
        return ""
    return "-".join(f"{int(p):02d}" if i else f"{int(p):04d}" for i, p in enumerate(parts[:3]))


def _external_ids(**ids: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in ids.items():
        if value is None:
            continue
        text = str(value).strip()
        if text:
            out[key] = text
    return out


def normalize_semantic_scholar(item: dict[str, Any]) -> dict[str, Any]:
    external = item.get("externalIds") or {}
    authors = [a.get("name", "") for a in item.get("authors") or [] if isinstance(a, dict) and a.get("name")]
    return {
        "provider_record_id": str(item.get("paperId") or ""),
        "canonical_ids": _external_ids(
            doi=external.get("DOI"),
            arxiv=external.get("ArXiv"),
            dblp=external.get("DBLP"),
            corpus_id=external.get("CorpusId") or item.get("corpusId"),
        ),
        "title": str(item.get("title") or "").strip(),
        "authors": authors,
        "publication_date": str(item.get("publicationDate") or item.get("year") or ""),
        "venue": str(item.get("venue") or ""),
        "url": str(item.get("url") or ""),
        "abstract": str(item.get("abstract") or ""),
        "citation_count": item.get("citationCount"),
        "reference_count": item.get("referenceCount"),
    }


def normalize_crossref(item: dict[str, Any]) -> dict[str, Any]:
    authors: list[str] = []
    for author in item.get("author") or []:
        if not isinstance(author, dict):
            continue
        name = " ".join(x for x in [str(author.get("given") or "").strip(), str(author.get("family") or "").strip()] if x)
        if name:
            authors.append(name)
    publication_date = (
        _date_parts(item.get("published-print"))
        or _date_parts(item.get("published-online"))
        or _date_parts(item.get("published"))
        or _date_parts(item.get("created"))
    )
    doi = str(item.get("DOI") or "").strip()
    return {
        "provider_record_id": doi,
        "canonical_ids": _external_ids(doi=doi),
        "title": _first(item.get("title")),
        "authors": authors,
        "publication_date": publication_date,
        "venue": _first(item.get("container-title")),
        "url": str(item.get("URL") or ""),
        "type": str(item.get("type") or ""),
        "citation_count": item.get("is-referenced-by-count"),
        "reference_count": len(item.get("reference") or []),
    }


def normalize_opencitations_meta(item: dict[str, Any]) -> dict[str, Any]:
    ids = str(item.get("id") or "")
    canonical: dict[str, str] = {}
    for token in ids.split():
        if ":" not in token:
            continue
        prefix, value = token.split(":", 1)
        if prefix.lower() in {"doi", "arxiv", "pmid", "pmcid"} and value:
            canonical[prefix.lower()] = value
    return {
        "provider_record_id": ids,
        "canonical_ids": canonical,
        "title": str(item.get("title") or "").strip(),
        "authors": [a.strip() for a in str(item.get("author") or "").split(";") if a.strip()],
        "publication_date": str(item.get("pub_date") or ""),
        "venue": str(item.get("venue") or ""),
        "type": str(item.get("type") or ""),
    }


def normalize_opencitations_edge(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider_record_id": str(item.get("oci") or item.get("citation") or ""),
        "citing": str(item.get("citing") or ""),
        "cited": str(item.get("cited") or ""),
        "creation": str(item.get("creation") or ""),
        "timespan": str(item.get("timespan") or ""),
    }


def make_signal(*, provider: str, operation: str, query: Any, raw: bytes, items: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "source_type": "discovery_signal",
        "epistemic_role": "triage_only",
        "provider": provider,
        "operation": operation,
        "query": query,
        "retrieved_at": now_iso(),
        "raw_metadata_hash": sha256_ref(raw),
        "item_count": len(items),
        "items": items,
        "metadata": metadata or {},
    }


def _headers(provider: str) -> dict[str, str]:
    contact = os.environ.get("RK_DISCOVERY_CONTACT", "").strip()
    headers = {
        "Accept": "application/json",
        "User-Agent": f"Research-Kernel-MCP-discovery/1.0{f' ({contact})' if contact else ''}",
    }
    if provider == "semantic_scholar":
        key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip()
        if key:
            headers["x-api-key"] = key
    elif provider == "opencitations":
        token = os.environ.get("OPENCITATIONS_TOKEN", "").strip()
        if token:
            headers["authorization"] = token
    return headers


def _request_json(url: str, *, provider: str, method: str = "GET", payload: Any | None = None, timeout: float = DEFAULT_TIMEOUT) -> tuple[Any, bytes]:
    body = None
    headers = _headers(provider)
    if payload is not None:
        body = canonical_json(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"{provider} HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{provider} request failed: {exc.reason}") from exc
    try:
        return json.loads(raw), raw
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{provider} returned non-JSON data") from exc


def semantic_search(query: str, limit: int, timeout: float) -> dict[str, Any]:
    fields = "paperId,corpusId,title,abstract,year,publicationDate,venue,url,externalIds,citationCount,referenceCount,authors"
    params = urllib.parse.urlencode({"query": query, "limit": limit, "fields": fields})
    data, raw = _request_json(f"{S2_GRAPH}/paper/search?{params}", provider="semantic_scholar", timeout=timeout)
    items = [normalize_semantic_scholar(x) for x in data.get("data") or [] if isinstance(x, dict)]
    return make_signal(provider="semantic_scholar", operation="paper_search", query=query, raw=raw, items=items, metadata={"total": data.get("total")})


def semantic_recommend(positive: list[str], negative: list[str], limit: int, timeout: float) -> dict[str, Any]:
    fields = "paperId,corpusId,title,abstract,year,publicationDate,venue,url,externalIds,citationCount,referenceCount,authors"
    params = urllib.parse.urlencode({"limit": limit, "fields": fields})
    payload = {"positivePaperIds": positive, "negativePaperIds": negative}
    data, raw = _request_json(f"{S2_RECOMMEND}/papers/?{params}", provider="semantic_scholar", method="POST", payload=payload, timeout=timeout)
    items = [normalize_semantic_scholar(x) for x in data.get("recommendedPapers") or [] if isinstance(x, dict)]
    return make_signal(provider="semantic_scholar", operation="recommendations", query=payload, raw=raw, items=items)


def crossref_search(query: str, limit: int, timeout: float) -> dict[str, Any]:
    args: dict[str, Any] = {"query.bibliographic": query, "rows": limit}
    contact = os.environ.get("RK_DISCOVERY_CONTACT", "").strip()
    if contact and "@" in contact:
        args["mailto"] = contact
    params = urllib.parse.urlencode(args)
    data, raw = _request_json(f"{CROSSREF}/works?{params}", provider="crossref", timeout=timeout)
    message = data.get("message") or {}
    items = [normalize_crossref(x) for x in message.get("items") or [] if isinstance(x, dict)]
    return make_signal(provider="crossref", operation="works_search", query=query, raw=raw, items=items, metadata={"total_results": message.get("total-results")})


def opencitations_meta(identifier: str, timeout: float) -> dict[str, Any]:
    encoded = urllib.parse.quote(identifier, safe=":")
    data, raw = _request_json(f"{OC_META}/metadata/{encoded}", provider="opencitations", timeout=timeout)
    rows = data if isinstance(data, list) else [data]
    items = [normalize_opencitations_meta(x) for x in rows if isinstance(x, dict)]
    return make_signal(provider="opencitations", operation="metadata", query=identifier, raw=raw, items=items)


def opencitations_edges(identifier: str, direction: str, timeout: float) -> dict[str, Any]:
    if direction not in {"references", "citations"}:
        raise ValueError("direction must be references or citations")
    encoded = urllib.parse.quote(identifier, safe=":")
    data, raw = _request_json(f"{OC_INDEX}/{direction}/{encoded}", provider="opencitations", timeout=timeout)
    rows = data if isinstance(data, list) else [data]
    items = [normalize_opencitations_edge(x) for x in rows if isinstance(x, dict)]
    return make_signal(provider="opencitations", operation=direction, query=identifier, raw=raw, items=items)


def _limit(value: int) -> int:
    return max(1, min(MAX_LIMIT, int(value)))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    sub = p.add_subparsers(dest="command", required=True)

    s2 = sub.add_parser("s2-search", help="Semantic Scholar paper search")
    s2.add_argument("query")
    s2.add_argument("--limit", type=int, default=DEFAULT_LIMIT)

    rec = sub.add_parser("s2-recommend", help="Semantic Scholar recommendations")
    rec.add_argument("--positive", action="append", required=True, help="Paper ID; repeat for multiple seeds")
    rec.add_argument("--negative", action="append", default=[], help="Negative paper ID; repeat as needed")
    rec.add_argument("--limit", type=int, default=DEFAULT_LIMIT)

    cr = sub.add_parser("crossref-search", help="Crossref bibliographic search")
    cr.add_argument("query")
    cr.add_argument("--limit", type=int, default=DEFAULT_LIMIT)

    ocm = sub.add_parser("oc-meta", help="OpenCitations Meta lookup, e.g. doi:10....")
    ocm.add_argument("identifier")

    oce = sub.add_parser("oc-edges", help="OpenCitations references/citations lookup")
    oce.add_argument("identifier")
    oce.add_argument("--direction", choices=["references", "citations"], default="references")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "s2-search":
            out = semantic_search(args.query, _limit(args.limit), args.timeout)
        elif args.command == "s2-recommend":
            out = semantic_recommend(args.positive, args.negative, _limit(args.limit), args.timeout)
        elif args.command == "crossref-search":
            out = crossref_search(args.query, _limit(args.limit), args.timeout)
        elif args.command == "oc-meta":
            out = opencitations_meta(args.identifier, args.timeout)
        elif args.command == "oc-edges":
            out = opencitations_edges(args.identifier, args.direction, args.timeout)
        else:  # pragma: no cover
            raise AssertionError(args.command)
    except (RuntimeError, ValueError) as exc:
        print(canonical_json({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(_clean(out), sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
