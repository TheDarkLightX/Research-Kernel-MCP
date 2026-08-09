from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import shutil
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from internal.research_kernel_mcp.kurate import (
    DISCOVERY_AUTHORITY,
    KURATE_PROVIDER,
    KurateBatch,
    candidate_receipt_ref,
    metric_score,
    validate_discovery_candidate,
)

ATOM_TYPES = {
    "OBSERVATION",
    "QUESTION",
    "HYPOTHESIS",
    "CLAIM",
    "EVIDENCE",
    "COUNTEREXAMPLE",
    "REFORMULATION",
    "EXPERIMENT",
    "RESULT",
    "RISK",
    "DECISION",
    "OPEN_PROBLEM",
}

STATUSES = {
    "DRAFT",
    "CANDIDATE",
    "UNKNOWN",
    "TESTABLE",
    "UNDER_TEST",
    "SUPPORTED",
    "REFUTED",
    "SUPERSEDED",
    "STALE",
}

EDGE_TYPES = {
    "SUPPORTS",
    "REFUTES",
    "DEPENDS_ON",
    "CONTRADICTS",
    "REFORMULATES",
    "GENERALIZES",
    "SPECIALIZES",
    "ANALOGIZES",
    "OPERATIONALIZES",
    "TESTS",
    "PRODUCES",
    "SUPERSEDES",
}

PROMOTABLE_STATUSES = {"SUPPORTED", "REFUTED", "SUPERSEDED", "STALE", "CANDIDATE", "TESTABLE", "UNDER_TEST"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_research_home() -> Path:
    return repo_root() / "internal" / "research_kernel"


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def pretty_json(obj: Any) -> str:
    return json.dumps(redact_value(obj), sort_keys=True, indent=2, ensure_ascii=False)


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_ref(data: bytes) -> str:
    return "sha256:" + sha256_hex(data)


SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password|private[_-]?key|bearer)\b\s*[:=]\s*['\"]?([^\s'\";]+)"
)
LONG_SECRET_RE = re.compile(r"\b[A-Za-z0-9_\-+=]{32,}\b")


def redact_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    redacted = SECRET_ASSIGNMENT_RE.sub(lambda m: f"{m.group(1)}=<REDACTED>", value)

    def _redact_long(match: re.Match[str]) -> str:
        token = match.group(0)
        if token.startswith(("sha256:", "http://", "https://", "rk://")):
            return token
        if re.fullmatch(r"[0-9a-f]{32,64}", token):
            return token
        return "<REDACTED>"

    return LONG_SECRET_RE.sub(_redact_long, redacted)


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(v) for v in value]
    return redact_text(value)


def normalize_content(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip().lower())


def parse_json_object(raw: str | None, *, default: dict[str, Any] | None = None, field: str = "json") -> dict[str, Any]:
    if raw is None or str(raw).strip() == "":
        return dict(default or {})
    try:
        obj = json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field} must be a JSON object: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError(f"{field} must be a JSON object")
    return obj


def parse_json_list(raw: str | None, *, default: list[Any] | None = None, field: str = "json") -> list[Any]:
    if raw is None or str(raw).strip() == "":
        return list(default or [])
    try:
        obj = json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field} must be a JSON list: {exc}") from exc
    if not isinstance(obj, list):
        raise ValueError(f"{field} must be a JSON list")
    return obj


def normalize_atom_type(value: str) -> str:
    normalized = str(value or "").strip().upper().replace("-", "_")
    if normalized not in ATOM_TYPES:
        raise ValueError(f"unknown atom type: {value}")
    return normalized


def normalize_status(value: str | None, *, default: str = "UNKNOWN") -> str:
    normalized = str(value or default).strip().upper().replace("-", "_")
    if normalized not in STATUSES:
        raise ValueError(f"unknown status: {value}")
    return normalized


def normalize_edge_type(value: str) -> str:
    normalized = str(value or "").strip().upper().replace("-", "_")
    if normalized not in EDGE_TYPES:
        raise ValueError(f"unknown edge type: {value}")
    return normalized


def clamp_score(value: float | int | None, *, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    return max(0.0, min(1.0, float(value)))


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


@dataclass(frozen=True)
class KernelConfig:
    home: Path
    repo: Path
    mode: str = "safe"

    @classmethod
    def from_env(cls) -> "KernelConfig":
        home = Path(os.environ.get("RESEARCH_HOME", str(default_research_home()))).expanduser().resolve()
        mode = os.environ.get("RK_MODE", "safe").strip() or "safe"
        return cls(home=home, repo=repo_root(), mode=mode)


class ResearchKernel:
    """Durable, evidence-first research substrate.

    The kernel stores public research artifacts only. It does not execute shell
    commands, browse the network, or attempt to persist private reasoning.
    """

    def __init__(self, home: Path | str | None = None, *, mode: str = "safe") -> None:
        self.repo = repo_root()
        self.home = Path(home).expanduser().resolve() if home is not None else default_research_home().resolve()
        self.mode = str(mode or "safe")
        self.db_path = self.home / "research_kernel.sqlite3"
        self.event_log_path = self.home / "events.jsonl"
        self.artifact_root = self.home / "artifacts"
        self.home.mkdir(parents=True, exist_ok=True)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @classmethod
    def from_env(cls) -> "ResearchKernel":
        cfg = KernelConfig.from_env()
        return cls(cfg.home, mode=cfg.mode)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs(
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    budget_json TEXT NOT NULL,
                    constraints_json TEXT NOT NULL,
                    success_criteria TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS atoms(
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    normalized_content TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL,
                    evidence_score REAL NOT NULL,
                    novelty_score REAL NOT NULL,
                    refutability_score REAL NOT NULL,
                    importance_score REAL NOT NULL,
                    uncertainty_score REAL NOT NULL,
                    hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source_refs_json TEXT NOT NULL,
                    artifact_refs_json TEXT NOT NULL,
                    parent_ids_json TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS edges(
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    source_atom_id TEXT NOT NULL REFERENCES atoms(id),
                    target_atom_id TEXT NOT NULL REFERENCES atoms(id),
                    edge_type TEXT NOT NULL,
                    weight REAL NOT NULL,
                    rationale TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evidence(
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    atom_id TEXT NOT NULL REFERENCES atoms(id),
                    source_type TEXT NOT NULL,
                    source_uri TEXT NOT NULL,
                    quote TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    reliability REAL NOT NULL,
                    artifact_hash TEXT,
                    captured_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS artifacts(
                    hash TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    path TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    provenance_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS experiments(
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    atom_id TEXT REFERENCES atoms(id),
                    command TEXT NOT NULL,
                    environment_hash TEXT NOT NULL,
                    seed TEXT NOT NULL,
                    input_hash TEXT NOT NULL,
                    output_hash TEXT NOT NULL,
                    result_status TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS promotions(
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    claim_atom_id TEXT NOT NULL REFERENCES atoms(id),
                    from_status TEXT NOT NULL,
                    to_status TEXT NOT NULL,
                    gate_result_json TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_atoms_run_status ON atoms(run_id, status);
                CREATE INDEX IF NOT EXISTS idx_atoms_type ON atoms(type);
                CREATE INDEX IF NOT EXISTS idx_edges_run_source ON edges(run_id, source_atom_id);
                CREATE INDEX IF NOT EXISTS idx_edges_run_target ON edges(run_id, target_atom_id);
                CREATE INDEX IF NOT EXISTS idx_evidence_atom ON evidence(atom_id);
                CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);
                """
            )
            try:
                conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS atoms_fts USING fts5(atom_id UNINDEXED, content, normalized_content, tags)"
                )
            except sqlite3.OperationalError:
                pass

    def _append_event(self, conn: sqlite3.Connection, run_id: str | None, event_type: str, payload: dict[str, Any]) -> None:
        created_at = now_iso()
        cur = conn.execute(
            "INSERT INTO events(run_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (run_id, event_type, canonical_json(payload), created_at),
        )
        record = {
            "id": int(cur.lastrowid),
            "run_id": run_id,
            "event_type": event_type,
            "payload": payload,
            "created_at": created_at,
        }
        with self.event_log_path.open("a", encoding="utf-8") as fh:
            fh.write(canonical_json(record) + "\n")

    def _has_fts(self, conn: sqlite3.Connection) -> bool:
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='atoms_fts'").fetchone()
        return row is not None

    def _upsert_fts(self, conn: sqlite3.Connection, atom: dict[str, Any]) -> None:
        if not self._has_fts(conn):
            return
        conn.execute("DELETE FROM atoms_fts WHERE atom_id = ?", (atom["id"],))
        conn.execute(
            "INSERT INTO atoms_fts(atom_id, content, normalized_content, tags) VALUES (?, ?, ?, ?)",
            (
                atom["id"],
                atom["content"],
                atom["normalized_content"],
                " ".join(atom.get("tags", [])),
            ),
        )

    def start_run(
        self,
        *,
        goal: str,
        title: str = "",
        constraints: dict[str, Any] | None = None,
        budget: dict[str, Any] | None = None,
        domain: str = "",
        success_criteria: str = "",
        metadata: dict[str, Any] | None = None,
        run_id: str = "",
    ) -> dict[str, Any]:
        goal = str(goal or "").strip()
        if not goal:
            raise ValueError("goal is required")
        rid = str(run_id or "").strip() or _id("run")
        ts = now_iso()
        md = dict(metadata or {})
        if domain:
            md["domain"] = str(domain)
        title = str(title or "").strip() or goal[:80]
        with self._connect() as conn:
            existing = conn.execute("SELECT * FROM runs WHERE id = ?", (rid,)).fetchone()
            if existing:
                conn.execute(
                    "UPDATE runs SET updated_at = ?, status = CASE WHEN status = 'ARCHIVED' THEN status ELSE 'ACTIVE' END WHERE id = ?",
                    (ts, rid),
                )
                self._append_event(conn, rid, "run_resumed", {"run_id": rid})
            else:
                conn.execute(
                    """
                    INSERT INTO runs(id, title, goal, status, created_at, updated_at,
                                     budget_json, constraints_json, success_criteria, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rid,
                        title,
                        goal,
                        "ACTIVE",
                        ts,
                        ts,
                        canonical_json(budget or {}),
                        canonical_json(constraints or {}),
                        str(success_criteria or ""),
                        canonical_json(md),
                    ),
                )
                self._append_event(conn, rid, "run_started", {"run_id": rid, "goal": goal})
        return self.run_summary(rid)

    def _get_run(self, conn: sqlite3.Connection, run_id: str) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise ValueError(f"unknown run_id: {run_id}")
        return row

    def _get_atom(self, conn: sqlite3.Connection, atom_id: str) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM atoms WHERE id = ?", (atom_id,)).fetchone()
        if row is None:
            raise ValueError(f"unknown atom_id: {atom_id}")
        return row

    def _row_atom(self, row: sqlite3.Row) -> dict[str, Any]:
        obj = dict(row)
        obj["source_refs"] = json.loads(obj.pop("source_refs_json"))
        obj["artifact_refs"] = json.loads(obj.pop("artifact_refs_json"))
        obj["parent_ids"] = json.loads(obj.pop("parent_ids_json"))
        obj["tags"] = json.loads(obj.pop("tags_json"))
        obj["metadata"] = json.loads(obj.pop("metadata_json"))
        return obj

    def _row_run(self, row: sqlite3.Row) -> dict[str, Any]:
        obj = dict(row)
        obj["budget"] = json.loads(obj.pop("budget_json"))
        obj["constraints"] = json.loads(obj.pop("constraints_json"))
        obj["metadata"] = json.loads(obj.pop("metadata_json"))
        return obj

    def atom_add(
        self,
        *,
        run_id: str,
        atom_type: str,
        content: str,
        status: str = "UNKNOWN",
        confidence: float | None = None,
        evidence_score: float = 0.0,
        novelty_score: float = 0.5,
        refutability_score: float = 0.5,
        importance_score: float = 0.5,
        uncertainty_score: float = 0.5,
        source_refs: list[str] | None = None,
        artifact_refs: list[str] | None = None,
        parent_ids: list[str] | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        atom_id: str = "",
    ) -> dict[str, Any]:
        content = str(content or "").strip()
        if not content:
            raise ValueError("content is required")
        kind = normalize_atom_type(atom_type)
        stat = normalize_status(status)
        aid = str(atom_id or "").strip() or _id("atom")
        normalized = normalize_content(content)
        parent_ids = [str(x) for x in (parent_ids or []) if str(x).strip()]
        tags = sorted({str(x).strip() for x in (tags or []) if str(x).strip()})
        source_refs = [str(x) for x in (source_refs or []) if str(x).strip()]
        artifact_refs = [str(x) for x in (artifact_refs or []) if str(x).strip()]
        metadata = dict(metadata or {})
        payload_for_hash = {
            "run_id": run_id,
            "type": kind,
            "content": normalized,
            "parents": parent_ids,
            "tags": tags,
        }
        digest = sha256_ref(canonical_json(payload_for_hash).encode("utf-8"))
        ts = now_iso()
        with self._connect() as conn:
            self._get_run(conn, run_id)
            for parent_id in parent_ids:
                self._get_atom(conn, parent_id)
            conn.execute(
                """
                INSERT INTO atoms(id, run_id, type, content, normalized_content, status,
                                  confidence, evidence_score, novelty_score, refutability_score,
                                  importance_score, uncertainty_score, hash, created_at, updated_at,
                                  source_refs_json, artifact_refs_json, parent_ids_json, tags_json, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    aid,
                    run_id,
                    kind,
                    content,
                    normalized,
                    stat,
                    confidence,
                    clamp_score(evidence_score),
                    clamp_score(novelty_score, default=0.5),
                    clamp_score(refutability_score, default=0.5),
                    clamp_score(importance_score, default=0.5),
                    clamp_score(uncertainty_score, default=0.5),
                    digest,
                    ts,
                    ts,
                    canonical_json(source_refs),
                    canonical_json(artifact_refs),
                    canonical_json(parent_ids),
                    canonical_json(tags),
                    canonical_json(metadata),
                ),
            )
            row = self._get_atom(conn, aid)
            atom = self._row_atom(row)
            self._upsert_fts(conn, atom)
            for parent_id in parent_ids:
                edge_id = _id("edge")
                conn.execute(
                    """
                    INSERT INTO edges(id, run_id, source_atom_id, target_atom_id, edge_type, weight, rationale, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (edge_id, run_id, aid, parent_id, "DEPENDS_ON", 1.0, "parent dependency", ts),
                )
                self._append_event(
                    conn,
                    run_id,
                    "edge_added",
                    {"edge_id": edge_id, "source_atom_id": aid, "target_atom_id": parent_id, "edge_type": "DEPENDS_ON"},
                )
            self._append_event(conn, run_id, "atom_added", {"atom_id": aid, "type": kind, "status": stat})
        return {"ok": True, "atom": atom}

    def link(
        self,
        *,
        run_id: str,
        source_atom_id: str,
        target_atom_id: str,
        edge_type: str,
        weight: float = 1.0,
        rationale: str = "",
        edge_id: str = "",
    ) -> dict[str, Any]:
        et = normalize_edge_type(edge_type)
        eid = str(edge_id or "").strip() or _id("edge")
        ts = now_iso()
        with self._connect() as conn:
            self._get_run(conn, run_id)
            self._get_atom(conn, source_atom_id)
            self._get_atom(conn, target_atom_id)
            conn.execute(
                """
                INSERT INTO edges(id, run_id, source_atom_id, target_atom_id, edge_type, weight, rationale, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (eid, run_id, source_atom_id, target_atom_id, et, clamp_score(weight, default=1.0), str(rationale or ""), ts),
            )
            self._append_event(
                conn,
                run_id,
                "edge_added",
                {"edge_id": eid, "source_atom_id": source_atom_id, "target_atom_id": target_atom_id, "edge_type": et},
            )
        return {"ok": True, "edge": self.get_edge(eid)}

    def get_edge(self, edge_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM edges WHERE id = ?", (edge_id,)).fetchone()
            if row is None:
                raise ValueError(f"unknown edge_id: {edge_id}")
            return dict(row)

    def get_atom(self, atom_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            return self._row_atom(self._get_atom(conn, atom_id))

    def _discovery_atoms_for_work(self, *, run_id: str, work_key: str) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM atoms WHERE run_id = ? AND type = 'RESULT' ORDER BY created_at DESC, id DESC",
                (run_id,),
            ).fetchall()
            for row in rows:
                atom = self._row_atom(row)
                discovery = atom.get("metadata", {}).get("discovery")
                if isinstance(discovery, dict) and discovery.get("work_key") == work_key:
                    matches.append(atom)
        return matches

    def import_kurate_batch(
        self,
        *,
        run_id: str,
        batch: KurateBatch,
        apply_triage_scores: bool = False,
    ) -> dict[str, Any]:
        """Store Kurate output as triage-only RESULT atoms.

        The imported evidence types are intentionally absent from the promotion
        gate's supporting-evidence allowlist. A Kurate assessment can prioritize
        primary-source review, but cannot support a claim by itself.
        """

        with self._connect() as conn:
            self._get_run(conn, run_id)
        if not batch.candidates:
            candidate_count = 0
        else:
            candidate_count = len(batch.candidates)
        query_text = canonical_json(batch.query)
        sweep = self.atom_add(
            run_id=run_id,
            atom_type="EXPERIMENT",
            content=f"Kurate discovery sweep returned {candidate_count} triage-only candidates for {query_text}.",
            status="CANDIDATE",
            evidence_score=0.0,
            uncertainty_score=1.0,
            tags=["discovery", "kurate", "triage-only"],
            metadata={
                "provider": KURATE_PROVIDER,
                "authority": DISCOVERY_AUTHORITY,
                "query": batch.query,
                "request_uri": batch.request_uri,
                "snapshot_ref": batch.snapshot_ref,
                "raw_response_ref": batch.raw_response_ref,
                "does_not_support_claims": True,
            },
        )["atom"]
        self.evidence_attach(
            run_id=run_id,
            atom_id=sweep["id"],
            source_type="kurate_discovery_batch",
            source_uri=batch.request_uri,
            summary="Raw Kurate discovery response. This is a triage signal, not supporting evidence.",
            reliability=0.0,
            artifact_text=batch.raw_response.decode("utf-8"),
            metadata={
                "authority": DISCOVERY_AUTHORITY,
                "snapshot_ref": batch.snapshot_ref,
                "raw_response_ref": batch.raw_response_ref,
                "does_not_support_claims": True,
            },
        )

        imported: list[dict[str, Any]] = []
        for candidate in batch.candidates:
            validate_discovery_candidate(candidate)
            receipt_ref = candidate_receipt_ref(candidate)
            identity = canonical_json({"run_id": run_id, "receipt_ref": receipt_ref}).encode("utf-8")
            atom_id = "result_kurate_" + sha256_hex(identity)[:24]
            try:
                self.get_atom(atom_id)
                created = False
            except ValueError:
                paper = candidate["paper"]
                if apply_triage_scores:
                    novelty_score = metric_score(candidate, "novelty")
                    importance_score = metric_score(candidate, "significance")
                    refutability_score = metric_score(candidate, "refutation_value")
                else:
                    novelty_score = 0.5
                    importance_score = 0.5
                    refutability_score = 0.5
                self.atom_add(
                    run_id=run_id,
                    atom_type="RESULT",
                    content=f"Kurate discovery candidate: {paper['title']} ({paper['arxiv_id']}).",
                    status="CANDIDATE",
                    confidence=None,
                    evidence_score=0.0,
                    novelty_score=novelty_score,
                    refutability_score=refutability_score,
                    importance_score=importance_score,
                    uncertainty_score=1.0,
                    source_refs=[candidate["provenance"]["paper_uri"]],
                    tags=[
                        "discovery",
                        "kurate",
                        "triage-only",
                        f"arxiv:{paper['arxiv_id_base']}",
                    ],
                    metadata={
                        "provider": KURATE_PROVIDER,
                        "authority": DISCOVERY_AUTHORITY,
                        "receipt_ref": receipt_ref,
                        "discovery": candidate,
                        "triage_scores_applied": bool(apply_triage_scores),
                        "does_not_support_claims": True,
                    },
                    atom_id=atom_id,
                )["atom"]
                self.evidence_attach(
                    run_id=run_id,
                    atom_id=atom_id,
                    source_type="kurate_discovery",
                    source_uri=candidate["provenance"]["paper_uri"],
                    summary="Kurate assessment imported for literature triage only; verify the exact primary source before attaching paper evidence to a claim.",
                    reliability=0.0,
                    artifact_text=canonical_json(candidate),
                    metadata={
                        "authority": DISCOVERY_AUTHORITY,
                        "receipt_ref": receipt_ref,
                        "does_not_support_claims": True,
                    },
                )
                for prior in self._discovery_atoms_for_work(
                    run_id=run_id,
                    work_key=str(candidate["work_key"]),
                ):
                    if prior["id"] == atom_id or prior["status"] == "SUPERSEDED":
                        continue
                    self.link(
                        run_id=run_id,
                        source_atom_id=atom_id,
                        target_atom_id=prior["id"],
                        edge_type="SUPERSEDES",
                        rationale="New Kurate snapshot for the same arXiv work.",
                    )
                    self.promote(
                        claim_atom_id=prior["id"],
                        to_status="SUPERSEDED",
                        rationale="A newer Kurate discovery receipt was imported for the same arXiv work.",
                    )
                created = True

            produced = self.link(
                run_id=run_id,
                source_atom_id=sweep["id"],
                target_atom_id=atom_id,
                edge_type="PRODUCES",
                rationale="The bounded Kurate sweep produced this triage-only candidate.",
            )["edge"]
            imported.append(
                {
                    "atom_id": atom_id,
                    "created": created,
                    "receipt_ref": receipt_ref,
                    "work_key": candidate["work_key"],
                    "produces_edge_id": produced["id"],
                }
            )

        return {
            "ok": True,
            "provider": KURATE_PROVIDER,
            "authority": DISCOVERY_AUTHORITY,
            "sweep_atom_id": sweep["id"],
            "snapshot_ref": batch.snapshot_ref,
            "raw_response_ref": batch.raw_response_ref,
            "candidates": imported,
            "non_claims": [
                "Kurate rankings and assessments are discovery signals, not peer review.",
                "No Kurate discovery evidence counts as support in the Research Kernel promotion gate.",
                "Primary-source applicability and independent checks remain required.",
            ],
        }

    def record_discovery_failure(
        self,
        *,
        run_id: str,
        provider: str,
        query: dict[str, Any],
        error_code: str,
        detail: str,
    ) -> dict[str, Any]:
        atom = self.atom_add(
            run_id=run_id,
            atom_type="OBSERVATION",
            content=f"{provider} discovery returned UNKNOWN ({error_code}); no candidates were imported.",
            status="UNKNOWN",
            evidence_score=0.0,
            uncertainty_score=1.0,
            tags=["discovery", provider, "negative-knowledge", "unknown"],
            metadata={
                "provider": provider,
                "authority": DISCOVERY_AUTHORITY,
                "query": query,
                "error": {"code": str(error_code), "detail": str(detail)},
                "does_not_support_claims": True,
            },
        )["atom"]
        return {
            "ok": False,
            "status": "UNKNOWN",
            "provider": provider,
            "failure_atom_id": atom["id"],
            "error": {"code": str(error_code), "detail": str(detail)},
        }

    def _allowed_artifact_roots(self) -> list[Path]:
        roots = [self.home.resolve(), self.repo.resolve()]
        extra = os.environ.get("RK_ARTIFACT_ALLOWLIST", "")
        for raw in extra.split(os.pathsep):
            if raw.strip():
                roots.append(Path(raw).expanduser().resolve())
        return roots

    def _validate_artifact_path(self, path: Path) -> Path:
        p = path.expanduser().resolve()
        if not p.exists() or not p.is_file():
            raise ValueError(f"artifact_path must be an existing file: {path}")
        if p.name == ".env" or p.name.endswith(".env"):
            raise ValueError("refusing to ingest .env files")
        if os.environ.get("RK_ALLOW_OUTSIDE_ARTIFACTS", "") == "1":
            return p
        roots = self._allowed_artifact_roots()
        if not any(p.is_relative_to(root) for root in roots):
            allowed = ", ".join(str(root) for root in roots)
            raise ValueError(f"artifact_path outside allowlist: {p}; allowed roots: {allowed}")
        return p

    def evidence_attach(
        self,
        *,
        run_id: str,
        atom_id: str,
        source_type: str,
        source_uri: str = "",
        quote: str = "",
        summary: str = "",
        reliability: float = 0.5,
        artifact_path: str = "",
        artifact_text: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        stype = str(source_type or "").strip().lower()
        if not stype:
            raise ValueError("source_type is required")
        if artifact_path and artifact_text:
            raise ValueError("provide artifact_path or artifact_text, not both")
        metadata = dict(metadata or {})
        artifact_hash: str | None = None
        artifact_record: dict[str, Any] | None = None
        ts = now_iso()
        with self._connect() as conn:
            self._get_run(conn, run_id)
            self._get_atom(conn, atom_id)
            if artifact_path:
                path = self._validate_artifact_path(Path(artifact_path))
                data = path.read_bytes()
                artifact_hash = sha256_ref(data)
                subdir = self.artifact_root / artifact_hash.split(":", 1)[1][:2]
                subdir.mkdir(parents=True, exist_ok=True)
                stored = subdir / artifact_hash.split(":", 1)[1]
                if not stored.exists():
                    shutil.copyfile(path, stored)
                mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
                provenance = {"original_path": str(path), "source_uri": str(source_uri or "")}
                conn.execute(
                    """
                    INSERT OR IGNORE INTO artifacts(hash, run_id, path, mime_type, size, created_at, provenance_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (artifact_hash, run_id, str(stored), mime, len(data), ts, canonical_json(provenance)),
                )
                artifact_record = {
                    "hash": artifact_hash,
                    "path": str(stored),
                    "mime_type": mime,
                    "size": len(data),
                    "provenance": provenance,
                }
            elif artifact_text:
                data = str(artifact_text).encode("utf-8")
                artifact_hash = sha256_ref(data)
                subdir = self.artifact_root / artifact_hash.split(":", 1)[1][:2]
                subdir.mkdir(parents=True, exist_ok=True)
                stored = subdir / artifact_hash.split(":", 1)[1]
                if not stored.exists():
                    stored.write_bytes(data)
                mime = "text/plain"
                provenance = {"kind": "inline_text", "source_uri": str(source_uri or "")}
                conn.execute(
                    """
                    INSERT OR IGNORE INTO artifacts(hash, run_id, path, mime_type, size, created_at, provenance_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (artifact_hash, run_id, str(stored), mime, len(data), ts, canonical_json(provenance)),
                )
                artifact_record = {
                    "hash": artifact_hash,
                    "path": str(stored),
                    "mime_type": mime,
                    "size": len(data),
                    "provenance": provenance,
                }
            eid = _id("evidence")
            conn.execute(
                """
                INSERT INTO evidence(id, run_id, atom_id, source_type, source_uri, quote, summary,
                                     reliability, artifact_hash, captured_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eid,
                    run_id,
                    atom_id,
                    stype,
                    str(source_uri or ""),
                    str(quote or ""),
                    str(summary or ""),
                    clamp_score(reliability, default=0.5),
                    artifact_hash,
                    ts,
                    canonical_json(metadata),
                ),
            )
            if artifact_hash or source_uri:
                atom = self._row_atom(self._get_atom(conn, atom_id))
                artifact_refs = sorted(set(atom["artifact_refs"] + ([artifact_hash] if artifact_hash else [])))
                source_refs = sorted(set(atom["source_refs"] + ([str(source_uri)] if source_uri else [])))
                conn.execute(
                    "UPDATE atoms SET source_refs_json = ?, artifact_refs_json = ?, updated_at = ? WHERE id = ?",
                    (canonical_json(source_refs), canonical_json(artifact_refs), ts, atom_id),
                )
            self._append_event(
                conn,
                run_id,
                "evidence_attached",
                {"evidence_id": eid, "atom_id": atom_id, "source_type": stype, "artifact_hash": artifact_hash},
            )
        evidence = self.get_evidence(eid)
        has_provenance = bool(evidence["source_uri"] or evidence["artifact_hash"])
        promotion_readiness = {
            "has_provenance": has_provenance,
        }
        if not has_provenance:
            promotion_readiness["hint"] = (
                "Promotion provenance requires source_uri, artifact_path, or artifact_text; "
                "summary-only evidence is support text, not replayable provenance."
            )
        return {
            "ok": True,
            "evidence": evidence,
            "artifact": artifact_record,
            "promotion_readiness": promotion_readiness,
        }

    def get_evidence(self, evidence_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,)).fetchone()
            if row is None:
                raise ValueError(f"unknown evidence_id: {evidence_id}")
            obj = dict(row)
            obj["metadata"] = json.loads(obj.pop("metadata_json"))
            return obj

    def refute(
        self,
        *,
        run_id: str,
        target_atom_id: str,
        strategy: str,
        tests: list[str] | None = None,
        counterexample: str = "",
        counterexample_is_actual: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        strategy = str(strategy or "").strip()
        if not strategy:
            raise ValueError("strategy is required")
        tests = [str(x) for x in (tests or []) if str(x).strip()]
        counterexample_text = str(counterexample or "").strip()
        actual_counterexample = bool(counterexample_is_actual)
        if actual_counterexample and not counterexample_text:
            raise ValueError("counterexample is required when counterexample_is_actual is true")
        kind = "COUNTEREXAMPLE" if actual_counterexample else "RISK"
        status = "REFUTED" if kind == "COUNTEREXAMPLE" else "UNDER_TEST"
        content = counterexample_text if actual_counterexample else strategy
        md = {"strategy": strategy, "tests": tests, **dict(metadata or {}), "actual_counterexample": actual_counterexample}
        if counterexample_text and not actual_counterexample:
            md["counterexample_context"] = counterexample_text
        atom = self.atom_add(
            run_id=run_id,
            atom_type=kind,
            content=content,
            status=status,
            refutability_score=1.0,
            importance_score=0.8,
            tags=["refutation"],
            metadata=md,
        )["atom"]
        edge_type = "REFUTES" if kind == "COUNTEREXAMPLE" else "TESTS"
        edge = self.link(
            run_id=run_id,
            source_atom_id=atom["id"],
            target_atom_id=target_atom_id,
            edge_type=edge_type,
            rationale=strategy,
        )["edge"]
        if kind == "COUNTEREXAMPLE":
            with self._connect() as conn:
                self._get_atom(conn, target_atom_id)
                ts = now_iso()
                conn.execute("UPDATE atoms SET status = ?, updated_at = ? WHERE id = ?", ("REFUTED", ts, target_atom_id))
                self._append_event(
                    conn,
                    run_id,
                    "atom_refuted",
                    {
                        "target_atom_id": target_atom_id,
                        "counterexample_atom_id": atom["id"],
                        "edge_id": edge["id"],
                        "actual_counterexample": True,
                    },
                )
        return {"ok": True, "refutation_atom": atom, "edge": edge, "actual_counterexample": actual_counterexample}

    def morph(
        self,
        *,
        target: str,
        run_id: str | None = None,
        modes: list[str] | None = None,
        constraints: dict[str, Any] | None = None,
        max_candidates: int = 8,
        store: bool = False,
    ) -> dict[str, Any]:
        target = str(target or "").strip()
        if not target:
            raise ValueError("target is required")
        modes = [str(m).strip() for m in (modes or ["equivalent_statement", "counterexample_search", "formal_spec"]) if str(m).strip()]
        constraints = dict(constraints or {})
        limit = max(1, min(32, int(max_candidates)))
        templates = {
            "equivalent_statement": ("Equivalent framing", "Restate as an explicit iff/contract: {target}"),
            "weaker_statement": ("Weaker statement", "Find minimal assumptions under which this remains true: {target}"),
            "stronger_statement": ("Stronger statement", "Ask whether this survives after strengthening the conclusion: {target}"),
            "dual_problem": ("Dual problem", "Search for a certificate or obstruction dual to: {target}"),
            "counterexample_search": ("Counterexample search", "Generate the smallest witness that falsifies: {target}"),
            "invariant_form": ("Invariant form", "Rewrite as a preserved invariant over transitions: {target}"),
            "optimization_form": ("Optimization form", "Rewrite as an objective, constraints, and tie-breaks: {target}"),
            "causal_form": ("Causal form", "Separate cause, mechanism, and observable effect in: {target}"),
            "graph_form": ("Graph form", "Map objects to nodes, typed edges, cuts, paths, or matchings for: {target}"),
            "benchmark_proxy": ("Benchmark proxy", "Define a bounded benchmark that would pressure-test: {target}"),
            "formal_spec": ("Formal spec", "Turn into assumptions, guarantees, reject cases, and proof obligations: {target}"),
            "implementation_obligation": ("Implementation obligation", "List code-level obligations required to make this true: {target}"),
            "attack_surface": ("Attack surface", "Enumerate adversarial ways this could fail: {target}"),
        }
        out: list[dict[str, Any]] = []
        for mode in modes:
            key = mode.strip().lower()
            title, statement_template = templates.get(key, (key.replace("_", " ").title(), "Reformulate this target through " + key + ": {target}"))
            relation = "equivalent" if key == "equivalent_statement" else "weaker" if key == "weaker_statement" else "stronger" if key == "stronger_statement" else "speculative"
            risk = "may change problem meaning" if relation == "speculative" else "check semantic preservation"
            item = {
                "id": f"R{len(out) + 1}",
                "mode": key,
                "title": title,
                "statement": statement_template.format(target=target),
                "relation_to_original": relation,
                "expected_value": round(0.55 + min(0.35, 0.03 * len(out) + (0.08 if key in {"counterexample_search", "formal_spec"} else 0.0)), 3),
                "risk": risk,
                "test": "Compare against the original on generated examples, prior failures, and contradiction memory.",
                "next_actions": ["retrieve prior failures", "attach evidence", "try a refutation before promotion"],
            }
            out.append(item)
            if len(out) >= limit:
                break
        stored_atoms: list[str] = []
        if store:
            if not run_id:
                raise ValueError("run_id is required when store=true")
            for item in out:
                atom = self.atom_add(
                    run_id=run_id,
                    atom_type="REFORMULATION",
                    content=item["statement"],
                    status="CANDIDATE",
                    novelty_score=0.6,
                    refutability_score=0.7,
                    importance_score=float(item["expected_value"]),
                    tags=["morph", item["mode"]],
                    metadata={"relation_to_original": item["relation_to_original"], "risk": item["risk"]},
                )["atom"]
                stored_atoms.append(atom["id"])
        if run_id:
            with self._connect() as conn:
                self._get_run(conn, run_id)
                self._append_event(conn, run_id, "morph_generated", {"target": target, "modes": modes, "stored_atoms": stored_atoms})
        return {"ok": True, "target": target, "reformulations": out, "stored_atom_ids": stored_atoms, "constraints": constraints}

    def _sanitize_fts_query(self, query: str) -> str:
        tokens = re.findall(r"[A-Za-z0-9_]+", query.lower())
        return " OR ".join(tokens[:16])

    def retrieve(
        self,
        *,
        query: str = "",
        run_id: str | None = None,
        modes: list[str] | None = None,
        atom_id: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        modes = [str(m).strip().lower() for m in (modes or ["similar_claims"]) if str(m).strip()]
        tags = [str(t).strip() for t in (tags or []) if str(t).strip()]
        limit_i = max(1, min(100, int(limit)))
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        with self._connect() as conn:
            if run_id:
                self._get_run(conn, run_id)
            if atom_id:
                self._get_atom(conn, atom_id)

            def add_atom(row: sqlite3.Row, reason: str, score: float) -> None:
                atom = self._row_atom(row)
                if tags and not set(tags).intersection(atom["tags"]):
                    return
                key = atom["id"] + ":" + reason
                if key in seen:
                    return
                seen.add(key)
                results.append({"reason": reason, "score": score, "atom": atom})

            if query.strip():
                if self._has_fts(conn):
                    fts_query = self._sanitize_fts_query(query)
                    if fts_query:
                        try:
                            rows = conn.execute(
                                """
                                SELECT atoms.*, bm25(atoms_fts) AS rank
                                FROM atoms_fts JOIN atoms ON atoms.id = atoms_fts.atom_id
                                WHERE atoms_fts MATCH ?
                                  AND (? = '' OR atoms.run_id = ?)
                                ORDER BY rank
                                LIMIT ?
                                """,
                                (fts_query, run_id or "", run_id or "", limit_i),
                            ).fetchall()
                            for row in rows:
                                add_atom(row, "lexical_or_semantic_proxy", 0.8)
                        except sqlite3.OperationalError:
                            pass
                if not results:
                    like = f"%{normalize_content(query)}%"
                    rows = conn.execute(
                        """
                        SELECT * FROM atoms
                        WHERE normalized_content LIKE ?
                          AND (? = '' OR run_id = ?)
                        ORDER BY updated_at DESC
                        LIMIT ?
                        """,
                        (like, run_id or "", run_id or "", limit_i),
                    ).fetchall()
                    for row in rows:
                        add_atom(row, "lexical_like", 0.5)

            if "prior_failures" in modes:
                rows = conn.execute(
                    """
                    SELECT * FROM atoms
                    WHERE status = 'REFUTED'
                      AND (? = '' OR run_id = ?)
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (run_id or "", run_id or "", limit_i),
                ).fetchall()
                for row in rows:
                    add_atom(row, "prior_failure", 0.9)

            if "open_frontier_matches" in modes or "old_run_memory" in modes:
                rows = conn.execute(
                    """
                    SELECT * FROM atoms
                    WHERE status IN ('UNKNOWN', 'CANDIDATE', 'TESTABLE', 'UNDER_TEST')
                      AND (? = '' OR run_id = ?)
                    ORDER BY importance_score + uncertainty_score + refutability_score DESC
                    LIMIT ?
                    """,
                    (run_id or "", run_id or "", limit_i),
                ).fetchall()
                for row in rows:
                    add_atom(row, "open_frontier", 0.7)

            if atom_id and ("graph_neighbors" in modes or "contradictory_evidence" in modes or "supporting_evidence" in modes):
                edge_filter = ""
                params: list[Any] = [atom_id, atom_id]
                if "contradictory_evidence" in modes and "supporting_evidence" not in modes:
                    edge_filter = "AND e.edge_type IN ('REFUTES', 'CONTRADICTS')"
                elif "supporting_evidence" in modes and "contradictory_evidence" not in modes:
                    edge_filter = "AND e.edge_type IN ('SUPPORTS', 'PRODUCES')"
                rows = conn.execute(
                    f"""
                    SELECT a.*, e.edge_type AS edge_reason
                    FROM edges e
                    JOIN atoms a ON a.id = CASE WHEN e.source_atom_id = ? THEN e.target_atom_id ELSE e.source_atom_id END
                    WHERE (e.source_atom_id = ? OR e.target_atom_id = ?)
                    {edge_filter}
                    LIMIT ?
                    """,
                    [atom_id, atom_id, atom_id, limit_i],
                ).fetchall()
                for row in rows:
                    add_atom(row, "graph_neighbor", 0.75)

            self._append_event(conn, run_id, "retrieve", {"query": query, "modes": modes, "atom_id": atom_id, "result_count": len(results)})
        results.sort(key=lambda item: item["score"], reverse=True)
        return {"ok": True, "query": query, "modes": modes, "results": results[:limit_i]}

    def score_atom(self, atom_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            atom = self._row_atom(self._get_atom(conn, atom_id))
            support_count = conn.execute(
                "SELECT COUNT(*) FROM edges WHERE target_atom_id = ? AND edge_type = 'SUPPORTS'",
                (atom_id,),
            ).fetchone()[0]
            refute_count = conn.execute(
                "SELECT COUNT(*) FROM edges WHERE target_atom_id = ? AND edge_type IN ('REFUTES', 'CONTRADICTS')",
                (atom_id,),
            ).fetchone()[0]
            evidence_count = conn.execute("SELECT COUNT(*) FROM evidence WHERE atom_id = ?", (atom_id,)).fetchone()[0]
        evidence_quality = min(1.0, evidence_count * 0.25 + support_count * 0.15)
        contradiction_penalty = min(1.0, refute_count * 0.25)
        atom_score = (
            evidence_quality
            + atom["refutability_score"]
            + atom["importance_score"]
            + atom["novelty_score"]
            + atom["uncertainty_score"] * 0.5
            - contradiction_penalty
        )
        priority = (
            atom["importance_score"]
            + atom["uncertainty_score"]
            + atom["refutability_score"]
            + atom["novelty_score"]
            + min(1.0, len(atom["parent_ids"]) * 0.15)
            - contradiction_penalty
        )
        return {
            "ok": True,
            "atom_id": atom_id,
            "atom_score": round(atom_score, 6),
            "priority": round(priority, 6),
            "components": {
                "evidence_quality": round(evidence_quality, 6),
                "support_count": support_count,
                "refute_or_contradict_count": refute_count,
                "evidence_count": evidence_count,
                "contradiction_penalty": round(contradiction_penalty, 6),
            },
        }

    def frontier(self, *, run_id: str, limit: int = 10) -> dict[str, Any]:
        limit_i = max(1, min(50, int(limit)))
        items: list[dict[str, Any]] = []
        with self._connect() as conn:
            self._get_run(conn, run_id)
            rows = conn.execute(
                """
                SELECT * FROM atoms
                WHERE run_id = ?
                  AND status IN ('UNKNOWN', 'CANDIDATE', 'TESTABLE', 'UNDER_TEST')
                """,
                (run_id,),
            ).fetchall()
        for row in rows:
            atom = self._row_atom(row)
            score = self.score_atom(atom["id"])
            items.append(
                {
                    "atom_id": atom["id"],
                    "type": atom["type"],
                    "status": atom["status"],
                    "content": atom["content"],
                    "priority": score["priority"],
                    "next_action": self._next_action(atom),
                    "tags": atom["tags"],
                }
            )
        items.sort(key=lambda item: (item["priority"], item["atom_id"]), reverse=True)
        return {"ok": True, "run_id": run_id, "frontier": items[:limit_i]}

    def _next_action(self, atom: dict[str, Any]) -> str:
        if atom["type"] in {"CLAIM", "HYPOTHESIS"} and atom["status"] in {"UNKNOWN", "CANDIDATE"}:
            return "attach evidence and run refutation search before promotion"
        if atom["type"] == "QUESTION":
            return "morph into testable hypotheses"
        if atom["type"] == "REFORMULATION":
            return "test equivalence or find a counterexample"
        return "retrieve similar failures and decide whether to refine, refute, or promote"

    def promote(
        self,
        *,
        claim_atom_id: str,
        to_status: str,
        rationale: str,
        checks: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        target = normalize_status(to_status)
        if target not in PROMOTABLE_STATUSES:
            raise ValueError(f"unsupported promotion target: {to_status}")
        rationale = str(rationale or "").strip()
        checks = dict(checks or {})
        if not rationale:
            raise ValueError("promotion rationale is required")
        with self._connect() as conn:
            atom_row = self._get_atom(conn, claim_atom_id)
            atom = self._row_atom(atom_row)
            run_id = atom["run_id"]
            current = atom["status"]
            evidence_rows = conn.execute("SELECT * FROM evidence WHERE atom_id = ?", (claim_atom_id,)).fetchall()
            edge_rows = conn.execute(
                "SELECT * FROM edges WHERE target_atom_id = ? OR source_atom_id = ?",
                (claim_atom_id, claim_atom_id),
            ).fetchall()
            dependencies = [e for e in edge_rows if e["edge_type"] == "DEPENDS_ON"] or atom["parent_ids"]
            support_evidence = [
                e
                for e in evidence_rows
                if e["source_type"] in {"source", "paper", "benchmark", "proof", "experiment", "test", "log", "artifact", "support"}
            ]
            refutation_attempts = [
                e for e in edge_rows if e["edge_type"] in {"TESTS", "REFUTES", "CONTRADICTS"}
            ] + [e for e in evidence_rows if e["source_type"] in {"refutation", "counterexample", "contradiction_search"}]
            evidence_with_provenance = [e["id"] for e in evidence_rows if e["source_uri"] or e["artifact_hash"]]
            evidence_without_provenance = [e["id"] for e in evidence_rows if not (e["source_uri"] or e["artifact_hash"])]
            provenance = bool(evidence_with_provenance)
            contradiction_search = bool(checks.get("contradiction_search_done")) or any(
                e["source_type"] == "contradiction_search" for e in evidence_rows
            )
            replay_recipe = bool(checks.get("replay_recipe")) or not checks.get("replay_required", False) or any(
                e["source_type"] in {"benchmark", "proof", "experiment", "test", "log"} for e in evidence_rows
            )
            counterexample_evidence = [e["id"] for e in evidence_rows if e["source_type"] == "counterexample"]
            refuting_edges = [e["id"] for e in edge_rows if e["edge_type"] in {"REFUTES", "CONTRADICTS"}]
            counterexample = bool(counterexample_evidence or refuting_edges)
            no_refuting_evidence = (not counterexample) and current != "REFUTED"
            supported_type = atom["type"] in {"CLAIM", "HYPOTHESIS", "RESULT", "DECISION"}
            claim_authority = atom.get("metadata", {}).get("authority") != DISCOVERY_AUTHORITY
            diagnostics: dict[str, Any] = {
                "evidence_with_provenance": evidence_with_provenance,
                "evidence_without_provenance": evidence_without_provenance,
                "counterexample_evidence": counterexample_evidence,
                "refuting_edges": refuting_edges,
            }
            if not provenance:
                diagnostics["provenance_hint"] = (
                    "Attach at least one evidence record with source_uri, artifact_path, or artifact_text "
                    "before promoting to SUPPORTED or REFUTED."
                )
            if counterexample:
                diagnostics["refutation_hint"] = (
                    "SUPPORT promotion is blocked while counterexample evidence or REFUTES/CONTRADICTS edges exist."
                )
            gate = {
                "target": target,
                "has_supported_type": bool(supported_type),
                "has_claim_authority": bool(claim_authority),
                "has_support_evidence": bool(support_evidence),
                "has_refutation_attempt": bool(refutation_attempts),
                "has_dependencies": bool(dependencies),
                "has_provenance": bool(provenance),
                "has_contradiction_search": bool(contradiction_search),
                "has_replay_recipe": bool(replay_recipe),
                "has_promotion_rationale": bool(rationale),
                "has_counterexample_or_refuting_evidence": bool(counterexample),
                "has_no_refuting_evidence": bool(no_refuting_evidence),
                "input_checks": checks,
                "diagnostics": diagnostics,
            }
            if target == "SUPPORTED":
                required = [
                    "has_supported_type",
                    "has_claim_authority",
                    "has_support_evidence",
                    "has_refutation_attempt",
                    "has_dependencies",
                    "has_provenance",
                    "has_contradiction_search",
                    "has_replay_recipe",
                    "has_promotion_rationale",
                    "has_no_refuting_evidence",
                ]
            elif target == "REFUTED":
                required = [
                    "has_claim_authority",
                    "has_counterexample_or_refuting_evidence",
                    "has_provenance",
                    "has_promotion_rationale",
                ]
            else:
                required = ["has_promotion_rationale"]
            missing = [key for key in required if not gate[key]]
            gate["ok"] = not missing
            gate["missing"] = missing
            pid = _id("promotion")
            ts = now_iso()
            conn.execute(
                """
                INSERT INTO promotions(id, run_id, claim_atom_id, from_status, to_status, gate_result_json, rationale, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (pid, run_id, claim_atom_id, current, target, canonical_json(gate), rationale, ts),
            )
            if not missing:
                conn.execute("UPDATE atoms SET status = ?, updated_at = ? WHERE id = ?", (target, ts, claim_atom_id))
            self._append_event(
                conn,
                run_id,
                "promotion_attempted",
                {"promotion_id": pid, "claim_atom_id": claim_atom_id, "to_status": target, "gate": gate},
            )
        return {"ok": not missing, "promotion_id": pid, "claim_atom_id": claim_atom_id, "from_status": current, "to_status": target, "gate": gate}

    def run_summary(self, run_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            run = self._row_run(self._get_run(conn, run_id))
            counts = {
                row["status"]: row["count"]
                for row in conn.execute("SELECT status, COUNT(*) AS count FROM atoms WHERE run_id = ? GROUP BY status", (run_id,))
            }
            type_counts = {
                row["type"]: row["count"]
                for row in conn.execute("SELECT type, COUNT(*) AS count FROM atoms WHERE run_id = ? GROUP BY type", (run_id,))
            }
            edge_count = conn.execute("SELECT COUNT(*) FROM edges WHERE run_id = ?", (run_id,)).fetchone()[0]
            evidence_count = conn.execute("SELECT COUNT(*) FROM evidence WHERE run_id = ?", (run_id,)).fetchone()[0]
            event_count = conn.execute("SELECT COUNT(*) FROM events WHERE run_id = ?", (run_id,)).fetchone()[0]
        return {
            "ok": True,
            "run": run,
            "counts_by_status": counts,
            "counts_by_type": type_counts,
            "edge_count": edge_count,
            "evidence_count": evidence_count,
            "event_count": event_count,
        }

    def graph(self, run_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            self._get_run(conn, run_id)
            atoms = [self._row_atom(row) for row in conn.execute("SELECT * FROM atoms WHERE run_id = ? ORDER BY created_at", (run_id,))]
            edges = [dict(row) for row in conn.execute("SELECT * FROM edges WHERE run_id = ? ORDER BY created_at", (run_id,))]
        return {"ok": True, "run_id": run_id, "atoms": atoms, "edges": edges}

    def report(self, *, run_id: str, include_graph: bool = False) -> dict[str, Any]:
        summary = self.run_summary(run_id)
        frontier = self.frontier(run_id=run_id, limit=10)
        with self._connect() as conn:
            supported = [self._row_atom(row) for row in conn.execute("SELECT * FROM atoms WHERE run_id = ? AND status = 'SUPPORTED'", (run_id,))]
            refuted = [self._row_atom(row) for row in conn.execute("SELECT * FROM atoms WHERE run_id = ? AND status = 'REFUTED'", (run_id,))]
            contradictions = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM edges WHERE run_id = ? AND edge_type IN ('REFUTES', 'CONTRADICTS') ORDER BY created_at DESC",
                    (run_id,),
                )
            ]
            latest_events = [
                dict(row)
                for row in conn.execute(
                    "SELECT id, event_type, payload_json, created_at FROM events WHERE run_id = ? ORDER BY id DESC LIMIT 20",
                    (run_id,),
                )
            ]
        report = {
            "ok": True,
            "schema": "research_kernel/report/v1",
            "summary": summary,
            "supported_claims": supported,
            "refuted_claims": refuted,
            "contradictions": contradictions,
            "frontier": frontier["frontier"],
            "latest_events": latest_events,
            "non_claims": [
                "Research Kernel stores public artifacts and evidence, not hidden chain-of-thought.",
                "SUPPORTED means the local promotion gate passed; it is not an external proof by itself.",
                "Morph reformulations are candidate search objects until separately tested.",
            ],
        }
        if include_graph:
            report["graph"] = self.graph(run_id)
        with self._connect() as conn:
            self._append_event(conn, run_id, "report_generated", {"include_graph": include_graph})
        return report

    def latest_report(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM runs ORDER BY updated_at DESC, created_at DESC LIMIT 1").fetchone()
            if row is None:
                return {"ok": True, "report": None}
            run_id = row["id"]
        return self.report(run_id=run_id, include_graph=False)

    def artifact(self, artifact_hash: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM artifacts WHERE hash = ?", (artifact_hash,)).fetchone()
            if row is None:
                raise ValueError(f"unknown artifact hash: {artifact_hash}")
            obj = dict(row)
            obj["provenance"] = json.loads(obj.pop("provenance_json"))
            return {"ok": True, "artifact": obj}

    def self_test(self) -> dict[str, Any]:
        run = self.start_run(goal="Research Kernel self-test", title="self-test")
        atom = self.atom_add(
            run_id=run["run"]["id"],
            atom_type="CLAIM",
            content="Research Kernel can persist a claim.",
            status="UNKNOWN",
            importance_score=0.4,
            refutability_score=0.7,
        )["atom"]
        retrieved = self.retrieve(query="persist claim", run_id=run["run"]["id"], modes=["similar_claims"], limit=5)
        return {
            "ok": bool(retrieved["results"]),
            "server": "research-kernel",
            "home": str(self.home),
            "db": str(self.db_path),
            "events_jsonl": str(self.event_log_path),
            "run_id": run["run"]["id"],
            "atom_id": atom["id"],
            "mode": self.mode,
        }
