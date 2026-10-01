from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
MODULE_PATH = TOOLS / "iacr_eprint_discovery.py"
spec = importlib.util.spec_from_file_location("iacr_eprint_discovery", MODULE_PATH)
assert spec is not None and spec.loader is not None
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


OAI_FIXTURE = b"""<?xml version='1.0' encoding='UTF-8'?>
<OAI-PMH xmlns='http://www.openarchives.org/OAI/2.0/'
         xmlns:oai_dc='http://www.openarchives.org/OAI/2.0/oai_dc/'
         xmlns:dc='http://purl.org/dc/elements/1.1/'>
  <responseDate>2026-08-09T00:00:00Z</responseDate>
  <request verb='GetRecord'>https://eprint.iacr.org/oai</request>
  <GetRecord>
    <record>
      <header>
        <identifier>oai:eprint.iacr.org:2026/1575</identifier>
        <datestamp>2026-08-03</datestamp>
      </header>
      <metadata>
        <oai_dc:dc>
          <dc:title>Solving the supersingular isogeny problem</dc:title>
          <dc:creator>Aleksei Udovenko</dc:creator>
          <dc:subject>isogenies</dc:subject>
          <dc:description>An abstract with   normalized whitespace.</dc:description>
          <dc:date>2026</dc:date>
          <dc:identifier>https://eprint.iacr.org/2026/1575</dc:identifier>
        </oai_dc:dc>
      </metadata>
    </record>
  </GetRecord>
</OAI-PMH>
"""

LIST_FIXTURE = b"""<?xml version='1.0' encoding='UTF-8'?>
<OAI-PMH xmlns='http://www.openarchives.org/OAI/2.0/'
         xmlns:oai_dc='http://www.openarchives.org/OAI/2.0/oai_dc/'
         xmlns:dc='http://purl.org/dc/elements/1.1/'>
  <ListRecords>
    <record>
      <header><identifier>oai:eprint.iacr.org:2026/1575</identifier></header>
      <metadata><oai_dc:dc>
        <dc:title>Paper A</dc:title><dc:creator>A</dc:creator>
        <dc:identifier>https://eprint.iacr.org/2026/1575</dc:identifier>
      </oai_dc:dc></metadata>
    </record>
    <record>
      <header><identifier>oai:eprint.iacr.org:2026/1576</identifier></header>
      <metadata><oai_dc:dc>
        <dc:title>Paper B</dc:title><dc:creator>B</dc:creator>
        <dc:identifier>https://ia.cr/2026/1576</dc:identifier>
      </oai_dc:dc></metadata>
    </record>
    <resumptionToken>next-page-token</resumptionToken>
  </ListRecords>
</OAI-PMH>
"""


def test_normalize_eprint_id() -> None:
    assert adapter.normalize_eprint_id("2026/1575") == "2026/1575"
    assert adapter.normalize_eprint_id("oai:eprint.iacr.org:2026/01575") == "2026/1575"
    assert adapter.normalize_eprint_id("https://ia.cr/2026/1575") == "2026/1575"


def test_parse_oai_get_record() -> None:
    items, token = adapter.parse_oai_records(OAI_FIXTURE)
    assert token == ""
    assert len(items) == 1
    item = items[0]
    assert item["provider_record_id"] == "2026/1575"
    assert item["canonical_ids"] == {"eprint": "2026/1575"}
    assert item["authors"] == ["Aleksei Udovenko"]
    assert item["abstract"] == "An abstract with normalized whitespace."
    assert item["subjects"] == ["isogenies"]


def test_parse_oai_list_records_and_token() -> None:
    items, token = adapter.parse_oai_records(LIST_FIXTURE)
    assert [x["canonical_ids"]["eprint"] for x in items] == ["2026/1575", "2026/1576"]
    assert token == "next-page-token"


def test_deleted_record_is_ignored() -> None:
    raw = b"""<OAI-PMH xmlns='http://www.openarchives.org/OAI/2.0/'>
      <ListRecords><record><header status='deleted'>
      <identifier>oai:eprint.iacr.org:2026/1</identifier>
      </header></record></ListRecords></OAI-PMH>"""
    items, token = adapter.parse_oai_records(raw)
    assert items == []
    assert token == ""
