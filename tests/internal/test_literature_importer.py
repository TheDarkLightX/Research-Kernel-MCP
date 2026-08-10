from __future__ import annotations

import hashlib
import json
from pathlib import Path

from internal.research_kernel_mcp.kernel import ResearchKernel
from internal.research_kernel_mcp.literature_importer import RECEIPT_SCHEMA, run


def mosaic_export() -> bytes:
    return json.dumps(
        {
            "status": "ok",
            "query": "checked abstraction",
            "count": 1,
            "papers": [
                {
                    "uid": "doi:10.1234/adapter",
                    "title": "Checked abstraction",
                    "authors": ["A. Author"],
                    "year": 2026,
                    "doi": "10.1234/adapter",
                    "source": "OpenAlex",
                    "is_open_access": True,
                    "relevance_score": 0.9,
                }
            ],
            "errors": [],
        },
        separators=(",", ":"),
    ).encode()


def args(tmp_path: Path, artifact: Path, digest: str) -> list[str]:
    return [
        "--home", str(tmp_path / "kernel"),
        "--run-id", "fleet-literature",
        "--goal", "Map prior art",
        "--artifact", str(artifact),
        "--artifact-sha256", digest,
        "--provider", "mosaic",
        "--receipt", str(tmp_path / "receipt.json"),
        "--import-id", "mosaic-broad",
        "--importer-id", "research-kernel",
    ]


def test_importer_binds_exact_export_and_triage_records(tmp_path: Path) -> None:
    artifact = tmp_path / "export.json"
    raw = mosaic_export()
    artifact.write_bytes(raw)
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()

    assert run(args(tmp_path, artifact, digest)) == 0
    receipt = json.loads((tmp_path / "receipt.json").read_text())
    assert receipt["schema"] == RECEIPT_SCHEMA
    assert receipt["status"] == "PASS"
    assert receipt["authority"] == "triage_only"
    assert receipt["artifact_sha256"] == digest
    assert receipt["external_refs"]

    kernel = ResearchKernel(tmp_path / "kernel")
    candidate_id = receipt["external_refs"][1].rsplit("/", 1)[-1]
    candidate = kernel.get_atom(candidate_id)
    assert candidate["status"] == "CANDIDATE"
    assert candidate["evidence_score"] == 0.0
    assert candidate["metadata"]["authority"] == "triage_only"


def test_importer_rejects_digest_mismatch_without_kernel_records(tmp_path: Path) -> None:
    artifact = tmp_path / "export.json"
    artifact.write_bytes(mosaic_export())

    assert run(args(tmp_path, artifact, "sha256:" + "0" * 64)) == 2
    receipt = json.loads((tmp_path / "receipt.json").read_text())
    assert receipt["status"] == "FAIL"
    assert receipt["external_refs"] == []
    assert not (tmp_path / "kernel" / "research_kernel.sqlite3").exists()
