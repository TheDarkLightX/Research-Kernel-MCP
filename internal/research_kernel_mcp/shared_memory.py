"""Selected-output bridge to the hosted Research Kernel memory pilot.

No transport, publication, network or scientific authority lives in this module.
Exported candidates and imported packages remain unverified research inputs.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .kernel import ResearchKernel

KINDS = {"hypothesis", "literature", "experiment", "formal", "bounded"}
PACKET_FIELDS = {"id", "hash", "claimId", "title", "claim", "receipts", "evidence", "createdAt", "license", "authority", "revoked"}
REVISION_FIELDS = {"title", "statement", "kind", "assumptions", "scope", "recipe", "dependencies", "number", "dependencyHashes", "hash", "author", "createdAt"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, field: str, maximum: int, minimum: int = 0) -> str:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise ValueError(f"{field} must be a string of {minimum}..{maximum} characters")
    return value


def _recipe(recipe: Any) -> None:
    if not isinstance(recipe, dict) or set(recipe) != {"checker", "variables", "left", "right"} or recipe["checker"] != "integer-grid/v1":
        raise ValueError("invalid bounded checker recipe")
    _text(recipe["left"], "left", 400, 1)
    _text(recipe["right"], "right", 400, 1)
    variables = recipe["variables"]
    if not isinstance(variables, dict) or not 1 <= len(variables) <= 3:
        raise ValueError("bounded recipes need 1..3 variables")
    count = 1
    for name, domain in variables.items():
        if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]{0,15}", name) or not isinstance(domain, dict) or set(domain) != {"min", "max"}:
            raise ValueError("invalid finite domain")
        lo, hi = domain["min"], domain["max"]
        if type(lo) is not int or type(hi) is not int or not -1000000 <= lo <= hi <= 1000000:
            raise ValueError("invalid finite integer bounds")
        count *= hi - lo + 1
    if count > 2048:
        raise ValueError("bounded recipes support at most 2048 cases")


def export_scoped_claim(
    kernel: ResearchKernel, *, atom_id: str, title: str, assumptions: str, scope: str,
    kind: str = "hypothesis", recipe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Export one explicit atom's statement; exclude scores, metadata and private runs."""
    atom = kernel.get_atom(atom_id)
    if atom["type"] not in {"CLAIM", "HYPOTHESIS", "RESULT"}:
        raise ValueError("select a CLAIM, HYPOTHESIS or RESULT atom")
    if kind not in KINDS:
        raise ValueError("invalid claim category")
    if kind == "bounded":
        _recipe(recipe)
    elif recipe is not None:
        raise ValueError("only bounded claims can have a checker recipe")
    claim = {
        "title": _text(title.strip(), "title", 180, 3),
        "statement": _text(atom["content"], "statement", 6000, 3),
        "kind": kind,
        "assumptions": _text(assumptions, "assumptions", 2000),
        "scope": _text(scope.strip(), "scope", 2000, 3),
        "recipe": recipe,
        "dependencies": [],
    }
    return {
        "schema": "rk-hosted-candidate/1", "command": {"type": "addClaim", "claim": claim},
        "authority": "unverified",
        "source": {"atom_id": atom_id, "atom_hash": atom["hash"]},
        "notices": [
            "The caller must review the selected statement and scope before sending it to a hosted workspace.",
            "Local status, confidence and discovery metadata were not exported as authority.",
            "Local dependency content and evidence attachments were not exported; select those separately.",
        ],
    }


def validate_package(packet: dict[str, Any]) -> None:
    if not isinstance(packet, dict) or set(packet) != PACKET_FIELDS:
        raise ValueError("invalid evidence package fields")
    if len(canonical(packet).encode("utf-8")) > 200000:
        raise ValueError("evidence package exceeds 200 KB")
    if packet["authority"] != "evidence-package" or packet["license"] != "CC-BY-4.0" or packet["revoked"] is not False:
        raise ValueError("invalid or revoked package")
    if not isinstance(packet["hash"], str) or not re.fullmatch("[a-f0-9]{64}", packet["hash"]):
        raise ValueError("invalid package fingerprint")
    value = {k: v for k, v in packet.items() if k not in {"hash", "revoked"}}
    if digest({"schema": "rk-evidence-package/1", **value}) != packet["hash"]:
        raise ValueError("evidence package digest mismatch")
    claim = packet["claim"]
    if not isinstance(claim, dict) or set(claim) != REVISION_FIELDS or claim["kind"] not in KINDS:
        raise ValueError("invalid claim contract")
    for field, maximum, minimum in [("title", 180, 3), ("statement", 6000, 3), ("scope", 2000, 3), ("assumptions", 2000, 0)]:
        _text(claim[field], field, maximum, minimum)
    contract = {k: v for k, v in claim.items() if k not in {"hash", "author", "createdAt"}}
    if digest(contract) != claim["hash"]:
        raise ValueError("claim revision digest mismatch")
    if claim["kind"] == "bounded":
        _recipe(claim["recipe"])
    elif claim["recipe"] is not None:
        raise ValueError("unexpected bounded recipe")
    if type(claim["number"]) is not int or claim["number"] < 1 or not isinstance(claim["dependencies"], list) or len(claim["dependencies"]) > 16:
        raise ValueError("invalid claim revision or dependency list")
    if not isinstance(claim["dependencyHashes"], dict) or set(claim["dependencyHashes"]) != set(claim["dependencies"]):
        raise ValueError("invalid dependency fingerprints")
    if not isinstance(packet["receipts"], list) or not isinstance(packet["evidence"], list) or len(packet["receipts"]) > 100 or len(packet["evidence"]) > 100:
        raise ValueError("invalid evidence or receipt list")
    for receipt in packet["receipts"]:
        if not isinstance(receipt, dict) or receipt.get("claimId") != packet["claimId"] or receipt.get("claimRevision") != claim["hash"] or receipt.get("authority") != "bounded-check-only":
            raise ValueError("receipt does not match selected claim")
        if claim["recipe"] is None or receipt.get("recipeHash") != digest(claim["recipe"]) or receipt.get("transcriptHash") != digest(receipt.get("result")):
            raise ValueError("receipt transcript fingerprint mismatch")
    for evidence in packet["evidence"]:
        if not isinstance(evidence, dict) or evidence.get("claimId") != packet["claimId"] or evidence.get("revisionHash") != claim["hash"] or evidence.get("authority") != "unverified":
            raise ValueError("evidence does not match selected claim")


def import_evidence_package(kernel: ResearchKernel, *, run_id: str, packet: dict[str, Any]) -> dict[str, Any]:
    """One local atom transaction; never import status, scores or proof authority."""
    validate_package(packet)
    atom_id = "shared_" + digest({"run": run_id, "packet": packet["hash"]})[:24]
    try:
        existing = kernel.get_atom(atom_id)
    except ValueError:
        existing = None
    if existing is not None:
        if existing["run_id"] != run_id or existing["metadata"].get("shared_memory", {}).get("packet_hash") != packet["hash"]:
            raise ValueError("import identity conflicts with an existing atom")
        return {"ok": True, "created": False, "atom": existing, "authority": "triage_only"}
    claim = packet["claim"]
    result = kernel.atom_add(
        run_id=run_id, atom_id=atom_id, atom_type="HYPOTHESIS", status="CANDIDATE",
        content=claim["statement"], confidence=None, evidence_score=0.0, uncertainty_score=1.0,
        source_refs=["rk-package:" + packet["hash"]], tags=["shared-memory", "triage-only", claim["kind"]],
        metadata={
            "authority": "triage_only", "does_not_support_claims": True,
            "shared_memory": {
                "packet_hash": packet["hash"], "claim_revision": claim["hash"], "license": packet["license"],
                "scope": claim["scope"], "assumptions": claim["assumptions"],
                "packet": packet, "verification": "External receipts are untrusted; independent local checking is required.",
            },
        },
    )
    return {"ok": True, "created": True, "atom": result["atom"], "authority": "triage_only"}
