"""Receipt-bound adapter from a frozen fleet export into Research Kernel."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from internal.research_kernel_mcp.kernel import ResearchKernel
from internal.research_kernel_mcp.literature import (
    MAX_EXPORT_BYTES,
    normalize_literature_export,
)

RECEIPT_SCHEMA = "codex-fleet-literature-import-receipt/v1"
ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,127}")
SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")


def sha_ref(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def write_receipt(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def receipt(
    *,
    importer_id: str,
    import_id: str,
    provider: str,
    artifact_sha256: str,
    status: str,
    external_refs: list[str],
    detail: str,
) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "importer_id": importer_id,
        "import_id": import_id,
        "provider": provider,
        "artifact_sha256": artifact_sha256,
        "status": status,
        "authority": "triage_only",
        "external_refs": external_refs,
        "detail": detail,
    }


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--artifact-sha256", required=True)
    parser.add_argument("--provider", choices=("citracer", "mosaic"), required=True)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--import-id", required=True)
    parser.add_argument("--importer-id", required=True)
    args = parser.parse_args(argv)
    for label, value in (("import-id", args.import_id), ("importer-id", args.importer_id)):
        if not ID_RE.fullmatch(value):
            parser.error(f"--{label} is invalid")
    if not SHA_RE.fullmatch(args.artifact_sha256):
        parser.error("--artifact-sha256 must be a sha256 reference")

    try:
        if args.artifact.stat().st_size > MAX_EXPORT_BYTES:
            raise ValueError("export exceeds 32 MiB")
        raw = args.artifact.read_bytes()
        if sha_ref(raw) != args.artifact_sha256:
            raise ValueError("artifact digest mismatch")
        batch = normalize_literature_export(
            raw,
            provider=args.provider,
            source_path=args.artifact.name,
        )
        kernel = ResearchKernel(args.home)
        kernel.start_run(
            goal=args.goal,
            run_id=args.run_id,
            metadata={"literature_import_authority": "triage_only"},
        )
        result = kernel.import_literature_batch(run_id=args.run_id, batch=batch)
        if sha_ref(args.artifact.read_bytes()) != args.artifact_sha256:
            raise ValueError("artifact changed during import")
        refs = [
            f"rk://run/{args.run_id}/atom/{result['sweep_atom_id']}",
            *(
                f"rk://run/{args.run_id}/atom/{item['atom_id']}"
                for item in result["candidates"]
            ),
            *(
                f"rk://run/{args.run_id}/edge/{item['edge_id']}"
                for item in result["relations"]
            ),
        ]
        value = receipt(
            importer_id=args.importer_id,
            import_id=args.import_id,
            provider=args.provider,
            artifact_sha256=args.artifact_sha256,
            status="PASS",
            external_refs=refs,
            detail=(
                f"Imported {len(result['candidates'])} candidates and "
                f"{len(result['relations'])} citation relations as triage-only records."
            ),
        )
        code = 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, sqlite3.Error) as exc:
        value = receipt(
            importer_id=args.importer_id,
            import_id=args.import_id,
            provider=args.provider,
            artifact_sha256=args.artifact_sha256,
            status="FAIL",
            external_refs=[],
            detail=f"{type(exc).__name__}: import rejected",
        )
        code = 2
    write_receipt(args.receipt, value)
    print(json.dumps(value, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(run())
