#!/usr/bin/env python3
"""Domain-first IACR Cryptology ePrint discovery for Research Kernel MCP.

This companion adapter keeps the deterministic ResearchKernel network-free while
making IACR ePrint a first-class cryptography discovery source.  It uses the
archive's OAI-PMH metadata interface and emits the same triage-only discovery
signal schema as ``research_discovery_adapter.py``.

Only Python's standard library is required.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from research_discovery_adapter import canonical_json, make_signal

OAI_BASE = "https://eprint.iacr.org/oai"
DEFAULT_TIMEOUT = 30.0
DEFAULT_LIMIT = 25
MAX_LIMIT = 200

OAI_NS = "http://www.openarchives.org/OAI/2.0/"
DC_NS = "http://purl.org/dc/elements/1.1/"
EPRINT_RE = re.compile(r"^(?P<year>\d{4})/(?P<number>\d{1,6})$")


def normalize_eprint_id(value: str) -> str:
    text = str(value or "").strip()
    text = text.removeprefix("oai:eprint.iacr.org:")
    text = text.removeprefix("https://eprint.iacr.org/")
    text = text.removeprefix("https://ia.cr/")
    text = text.strip("/")
    match = EPRINT_RE.fullmatch(text)
    if not match:
        raise ValueError("ePrint identifier must look like YYYY/NNNN")
    return f"{match.group('year')}/{int(match.group('number'))}"


def _text_values(node: ET.Element, tag: str) -> list[str]:
    values: list[str] = []
    for child in node.findall(f".//{{{DC_NS}}}{tag}"):
        value = " ".join((child.text or "").split())
        if value:
            values.append(value)
    return values


def _record_id(record: ET.Element) -> str:
    identifier = record.findtext(f"./{{{OAI_NS}}}header/{{{OAI_NS}}}identifier", default="").strip()
    if identifier:
        try:
            return normalize_eprint_id(identifier)
        except ValueError:
            pass
    metadata = record.find(f"./{{{OAI_NS}}}metadata")
    if metadata is not None:
        for value in _text_values(metadata, "identifier"):
            for prefix in ("https://eprint.iacr.org/", "https://ia.cr/"):
                if value.startswith(prefix):
                    try:
                        return normalize_eprint_id(value)
                    except ValueError:
                        continue
    return ""


def normalize_oai_record(record: ET.Element) -> dict[str, Any] | None:
    header = record.find(f"./{{{OAI_NS}}}header")
    if header is None or header.attrib.get("status") == "deleted":
        return None
    metadata = record.find(f"./{{{OAI_NS}}}metadata")
    if metadata is None:
        return None

    eprint_id = _record_id(record)
    titles = _text_values(metadata, "title")
    creators = _text_values(metadata, "creator")
    dates = _text_values(metadata, "date")
    descriptions = _text_values(metadata, "description")
    subjects = _text_values(metadata, "subject")
    identifiers = _text_values(metadata, "identifier")

    url = ""
    for value in identifiers:
        if value.startswith(("https://eprint.iacr.org/", "https://ia.cr/")):
            url = value
            break
    if not url and eprint_id:
        url = f"https://eprint.iacr.org/{eprint_id}"

    canonical_ids: dict[str, str] = {}
    if eprint_id:
        canonical_ids["eprint"] = eprint_id

    return {
        "provider_record_id": eprint_id or _record_id(record),
        "canonical_ids": canonical_ids,
        "title": titles[0] if titles else "",
        "authors": creators,
        "publication_date": dates[0] if dates else "",
        "url": url,
        "abstract": descriptions[0] if descriptions else "",
        "subjects": subjects,
        "all_identifiers": identifiers,
    }


def parse_oai_records(raw: bytes) -> tuple[list[dict[str, Any]], str]:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise RuntimeError(f"IACR OAI returned invalid XML: {exc}") from exc

    error = root.find(f".//{{{OAI_NS}}}error")
    if error is not None:
        code = error.attrib.get("code", "oai_error")
        detail = " ".join((error.text or "").split())
        raise RuntimeError(f"IACR OAI {code}: {detail}")

    items: list[dict[str, Any]] = []
    for record in root.findall(f".//{{{OAI_NS}}}record"):
        item = normalize_oai_record(record)
        if item is not None:
            items.append(item)

    token = root.findtext(f".//{{{OAI_NS}}}resumptionToken", default="").strip()
    return items, token


def _request_xml(params: dict[str, str], *, timeout: float, base_url: str = OAI_BASE) -> bytes:
    query = urllib.parse.urlencode(params)
    url = f"{base_url}?{query}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.1",
            "User-Agent": "Research-Kernel-MCP-IACR-discovery/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"IACR OAI HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"IACR OAI request failed: {exc.reason}") from exc


def get_paper(eprint_id: str, *, timeout: float, base_url: str = OAI_BASE) -> dict[str, Any]:
    eid = normalize_eprint_id(eprint_id)
    raw = _request_xml(
        {
            "verb": "GetRecord",
            "identifier": f"oai:eprint.iacr.org:{eid}",
            "metadataPrefix": "oai_dc",
        },
        timeout=timeout,
        base_url=base_url,
    )
    items, _token = parse_oai_records(raw)
    return make_signal(
        provider="iacr_eprint",
        operation="oai_get_record",
        query={"eprint": eid},
        raw=raw,
        items=items,
        metadata={"oai_base": base_url},
    )


def list_recent(
    *,
    from_date: str,
    until_date: str,
    limit: int,
    timeout: float,
    base_url: str = OAI_BASE,
) -> dict[str, Any]:
    target = max(1, min(MAX_LIMIT, int(limit)))
    items: list[dict[str, Any]] = []
    raw_pages: list[bytes] = []
    token = ""
    first = True

    while len(items) < target:
        if first:
            params = {"verb": "ListRecords", "metadataPrefix": "oai_dc"}
            if from_date:
                params["from"] = from_date
            if until_date:
                params["until"] = until_date
            first = False
        else:
            if not token:
                break
            params = {"verb": "ListRecords", "resumptionToken": token}

        raw = _request_xml(params, timeout=timeout, base_url=base_url)
        raw_pages.append(raw)
        page_items, token = parse_oai_records(raw)
        items.extend(page_items)
        if not token:
            break

    joined_raw = b"\n<!-- page boundary -->\n".join(raw_pages)
    query = {"from": from_date, "until": until_date, "limit": target}
    return make_signal(
        provider="iacr_eprint",
        operation="oai_list_records",
        query=query,
        raw=joined_raw,
        items=items[:target],
        metadata={"oai_base": base_url, "pages_fetched": len(raw_pages)},
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    p.add_argument("--base-url", default=OAI_BASE, help="Override the OAI-PMH base endpoint")
    sub = p.add_subparsers(dest="command", required=True)

    paper = sub.add_parser("paper", help="Fetch one ePrint metadata record")
    paper.add_argument("eprint_id", help="e.g. 2026/1575")

    recent = sub.add_parser("recent", help="List OAI records in a date window")
    recent.add_argument("--from-date", default="", help="OAI date, e.g. 2026-08-01")
    recent.add_argument("--until-date", default="", help="OAI date, e.g. 2026-08-09")
    recent.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "paper":
            out = get_paper(args.eprint_id, timeout=args.timeout, base_url=args.base_url)
        elif args.command == "recent":
            out = list_recent(
                from_date=args.from_date,
                until_date=args.until_date,
                limit=args.limit,
                timeout=args.timeout,
                base_url=args.base_url,
            )
        else:  # pragma: no cover
            raise AssertionError(args.command)
    except (RuntimeError, ValueError) as exc:
        print(canonical_json({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2
    print(__import__("json").dumps(out, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
