from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

DISCOVERY_CANDIDATE_SCHEMA_V1 = "research-discovery/candidate/v1"
DISCOVERY_AUTHORITY = "triage_only"
KURATE_PROVIDER = "kurate"
KURATE_BASE_URL = "https://kurate.org"
KURATE_MAX_LIMIT = 40
KURATE_MAX_RESPONSE_BYTES = 4 * 1024 * 1024

KURATE_METRICS = (
    "score",
    "significance",
    "rigor",
    "novelty",
    "clarity",
    "difficulty",
    "surprisingness",
    "reproducibility",
    "translational_potential",
    "evidence_strength",
    "generalisability",
    "interdisciplinarity",
    "refutation_value",
    "replication_value",
    "resource_intensity",
    "foundationality",
)
KURATE_SORT_KEYS = frozenset((*KURATE_METRICS, "published"))
KURATE_SORT_DIRECTIONS = frozenset(("asc", "desc"))

_CATEGORY_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_DATE_RANGE_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
_ARXIV_ID_RE = re.compile(r"^[A-Za-z0-9._/-]{3,64}$")
_VERSION_SUFFIX_RE = re.compile(r"v[1-9][0-9]*$")


class KurateAdapterError(ValueError):
    """Typed, public-safe failure at the Kurate network boundary."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = str(code)
        self.detail = str(detail)
        super().__init__(f"{self.code}: {self.detail}")


@dataclass(frozen=True)
class KurateBatch:
    request_uri: str
    query: dict[str, Any]
    candidates: tuple[dict[str, Any], ...]
    raw_response: bytes
    raw_response_ref: str
    snapshot_ref: str


def _sha256_ref(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return {"$decimal": format(value, "f")}
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(child) for child in value]
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _canonical_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise KurateAdapterError("MALFORMED_RESPONSE", f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(value: str) -> None:
    raise KurateAdapterError("MALFORMED_RESPONSE", f"non-finite JSON number: {value}")


def _parse_json(raw: bytes) -> Mapping[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise KurateAdapterError("MALFORMED_RESPONSE", "response is not UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_float=Decimal,
            parse_constant=_reject_constant,
        )
    except KurateAdapterError:
        raise
    except (json.JSONDecodeError, InvalidOperation, ValueError) as exc:
        raise KurateAdapterError("MALFORMED_RESPONSE", "response is not strict JSON") from exc
    if not isinstance(value, Mapping):
        raise KurateAdapterError("SCHEMA_DRIFT", "top-level response must be an object")
    return value


def _bounded_text(value: Any, field: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise KurateAdapterError("SCHEMA_DRIFT", f"{field} must be a non-empty string")
    text = value.strip()
    if len(text) > maximum:
        raise KurateAdapterError("SCHEMA_DRIFT", f"{field} exceeds {maximum} characters")
    return text


def _metric_milli(value: Any, metric: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise KurateAdapterError("SCHEMA_DRIFT", f"rating {metric} must be numeric or null")
    try:
        number = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise KurateAdapterError("SCHEMA_DRIFT", f"rating {metric} must be numeric or null") from exc
    if not number.is_finite() or number < 0 or number > 10:
        raise KurateAdapterError("SCHEMA_DRIFT", f"rating {metric} must be between 0 and 10")
    scaled = number * 1000
    if scaled != scaled.to_integral_value():
        raise KurateAdapterError("SCHEMA_DRIFT", f"rating {metric} has excessive precision")
    return int(scaled)


def _query_parameters(
    *,
    search: str,
    categories: Iterable[str],
    date_range: str,
    sort_key: str,
    sort_dir: str,
    limit: int,
    offset: int,
) -> tuple[list[tuple[str, str]], dict[str, Any]]:
    search_text = str(search or "").strip()
    if len(search_text) > 256:
        raise KurateAdapterError("INVALID_REQUEST", "search exceeds 256 characters")

    category_values = sorted({str(item).strip() for item in categories if str(item).strip()})
    if len(category_values) > 16:
        raise KurateAdapterError("INVALID_REQUEST", "at most 16 categories may be requested")
    if any(not _CATEGORY_RE.fullmatch(item) for item in category_values):
        raise KurateAdapterError("INVALID_REQUEST", "category contains unsafe characters")

    date_value = str(date_range or "all").strip() or "all"
    if not _DATE_RANGE_RE.fullmatch(date_value):
        raise KurateAdapterError("INVALID_REQUEST", "date_range contains unsafe characters")
    sort_value = str(sort_key or "score").strip()
    if sort_value not in KURATE_SORT_KEYS:
        raise KurateAdapterError("INVALID_REQUEST", f"unsupported sort_key: {sort_value}")
    direction = str(sort_dir or "desc").strip().lower()
    if direction not in KURATE_SORT_DIRECTIONS:
        raise KurateAdapterError("INVALID_REQUEST", f"unsupported sort_dir: {direction}")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= KURATE_MAX_LIMIT:
        raise KurateAdapterError("INVALID_REQUEST", f"limit must be between 1 and {KURATE_MAX_LIMIT}")
    if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= 1_000_000:
        raise KurateAdapterError("INVALID_REQUEST", "offset must be between 0 and 1000000")

    params = [
        ("dataset", "live"),
        ("sort_key", sort_value),
        ("sort_dir", direction),
        ("offset", str(offset)),
        ("limit", str(limit)),
        ("include_categories", "false"),
        ("include_histograms", "false"),
    ]
    if date_value != "all":
        params.append(("date_range", date_value))
    if category_values:
        params.append(("cats", ",".join(category_values)))
    if search_text:
        params.append(("search", search_text))
    query = {
        "search": search_text,
        "categories": category_values,
        "date_range": date_value,
        "sort_key": sort_value,
        "sort_dir": direction,
        "limit": limit,
        "offset": offset,
    }
    return params, query


def _read_response(response: Any) -> bytes:
    status = getattr(response, "status", 200)
    if not isinstance(status, int) or status < 200 or status >= 300:
        raise KurateAdapterError("REMOTE_HTTP_ERROR", f"Kurate returned HTTP {status}")
    raw = response.read(KURATE_MAX_RESPONSE_BYTES + 1)
    if not isinstance(raw, bytes):
        raise KurateAdapterError("MALFORMED_RESPONSE", "response body must be bytes")
    if len(raw) > KURATE_MAX_RESPONSE_BYTES:
        raise KurateAdapterError("RESPONSE_TOO_LARGE", "Kurate response exceeded 4 MiB")
    return raw


def _fetch_bytes(
    request_uri: str,
    *,
    timeout_seconds: int,
    opener: Callable[..., Any] | None,
    user_agent: str,
) -> bytes:
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 60:
        raise KurateAdapterError("INVALID_REQUEST", "timeout_seconds must be between 1 and 60")
    request = urllib.request.Request(
        request_uri,
        headers={"Accept": "application/json", "User-Agent": user_agent},
        method="GET",
    )
    open_fn = opener or urllib.request.urlopen
    try:
        response = open_fn(request, timeout=timeout_seconds)
        with response:
            return _read_response(response)
    except KurateAdapterError:
        raise
    except urllib.error.HTTPError as exc:
        raise KurateAdapterError("REMOTE_HTTP_ERROR", f"Kurate returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise KurateAdapterError("REMOTE_UNAVAILABLE", "Kurate could not be reached") from exc


def _normalize_row(
    row: Any,
    *,
    request_uri: str,
    snapshot_ref: str,
    sort_key: str,
    sort_dir: str,
    position: int,
    base_url: str,
) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        raise KurateAdapterError("SCHEMA_DRIFT", "paper row must be an object")
    paper_id = _bounded_text(row.get("paper_id"), "paper_id", maximum=128)
    arxiv_id = _bounded_text(row.get("arxiv_id"), "arxiv_id", maximum=64)
    if not _ARXIV_ID_RE.fullmatch(arxiv_id):
        raise KurateAdapterError("SCHEMA_DRIFT", "arxiv_id contains unsafe characters")
    arxiv_base = _VERSION_SUFFIX_RE.sub("", arxiv_id)
    title = _bounded_text(row.get("title"), "title", maximum=10_000)
    published = _bounded_text(row.get("published"), "published", maximum=128)

    authors_raw = row.get("authors")
    categories_raw = row.get("categories")
    if not isinstance(authors_raw, list) or len(authors_raw) > 1024:
        raise KurateAdapterError("SCHEMA_DRIFT", "authors must be a bounded list")
    if not isinstance(categories_raw, list) or len(categories_raw) > 64:
        raise KurateAdapterError("SCHEMA_DRIFT", "categories must be a bounded list")
    authors = [_bounded_text(item, "author", maximum=512) for item in authors_raw]
    categories = [_bounded_text(item, "category", maximum=64) for item in categories_raw]
    if any(not _CATEGORY_RE.fullmatch(item) for item in categories):
        raise KurateAdapterError("SCHEMA_DRIFT", "paper category contains unsafe characters")
    primary_category = _bounded_text(row.get("category"), "category", maximum=64)
    if not _CATEGORY_RE.fullmatch(primary_category):
        raise KurateAdapterError("SCHEMA_DRIFT", "primary category contains unsafe characters")

    ratings_raw = row.get("ratings")
    if not isinstance(ratings_raw, Mapping):
        raise KurateAdapterError("SCHEMA_DRIFT", "ratings must be an object")
    unknown_metrics = sorted({str(key) for key in ratings_raw} - set(KURATE_METRICS))
    if unknown_metrics:
        raise KurateAdapterError("SCHEMA_DRIFT", f"unknown rating fields: {', '.join(unknown_metrics)}")
    metrics_milli = {metric: _metric_milli(ratings_raw.get(metric), metric) for metric in KURATE_METRICS}

    return {
        "schema": DISCOVERY_CANDIDATE_SCHEMA_V1,
        "provider": KURATE_PROVIDER,
        "authority": DISCOVERY_AUTHORITY,
        "candidate_key": f"kurate:{paper_id}:{arxiv_id}",
        "work_key": f"arxiv:{arxiv_base}",
        "paper": {
            "provider_id": paper_id,
            "arxiv_id": arxiv_id,
            "arxiv_id_base": arxiv_base,
            "title": title,
            "authors": authors,
            "primary_category": primary_category,
            "categories": categories,
            "published": published,
        },
        "assessment": {
            "metrics_milli": metrics_milli,
            "scale": {"minimum": 0, "maximum": 10_000, "unit": "milli_point"},
        },
        "provenance": {
            "paper_uri": f"{base_url}/paper/{urllib.parse.quote(paper_id, safe='')}",
            "api_uri": request_uri,
            "snapshot_ref": snapshot_ref,
        },
        "selection": {"sort_key": sort_key, "sort_dir": sort_dir, "position": position},
    }


def normalize_kurate_response(
    raw: bytes,
    *,
    request_uri: str,
    query: Mapping[str, Any],
    base_url: str = KURATE_BASE_URL,
) -> KurateBatch:
    payload = _parse_json(raw)
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise KurateAdapterError("SCHEMA_DRIFT", "response rows must be a list")
    if len(rows) > int(query["limit"]):
        raise KurateAdapterError("SCHEMA_DRIFT", "response contains more rows than requested")
    semantic_snapshot = {
        "dataset": payload.get("dataset"),
        "total": payload.get("total"),
        "rows": rows,
    }
    try:
        snapshot_ref = _sha256_ref(_canonical_bytes(semantic_snapshot))
    except (TypeError, ValueError) as exc:
        raise KurateAdapterError("MALFORMED_RESPONSE", "response contains non-canonical values") from exc
    candidates = tuple(
        _normalize_row(
            row,
            request_uri=request_uri,
            snapshot_ref=snapshot_ref,
            sort_key=str(query["sort_key"]),
            sort_dir=str(query["sort_dir"]),
            position=int(query["offset"]) + index,
            base_url=base_url,
        )
        for index, row in enumerate(rows)
    )
    return KurateBatch(
        request_uri=request_uri,
        query=dict(query),
        candidates=candidates,
        raw_response=bytes(raw),
        raw_response_ref=_sha256_ref(raw),
        snapshot_ref=snapshot_ref,
    )


def fetch_kurate_candidates(
    *,
    search: str = "",
    categories: Iterable[str] = (),
    date_range: str = "all",
    sort_key: str = "score",
    sort_dir: str = "desc",
    limit: int = 10,
    offset: int = 0,
    timeout_seconds: int = 20,
    opener: Callable[..., Any] | None = None,
    base_url: str = KURATE_BASE_URL,
    user_agent: str = "ResearchKernelKurateAdapter/1.0",
) -> KurateBatch:
    normalized_base = str(base_url or "").rstrip("/")
    parsed_base = urllib.parse.urlsplit(normalized_base)
    if parsed_base.scheme != "https" or parsed_base.netloc != "kurate.org" or parsed_base.username or parsed_base.password:
        raise KurateAdapterError("INVALID_REQUEST", "base_url must be https://kurate.org")
    params, query = _query_parameters(
        search=search,
        categories=categories,
        date_range=date_range,
        sort_key=sort_key,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )
    request_uri = f"{normalized_base}/api/papers-list?{urllib.parse.urlencode(params)}"
    raw = _fetch_bytes(
        request_uri,
        timeout_seconds=timeout_seconds,
        opener=opener,
        user_agent=user_agent,
    )
    return normalize_kurate_response(raw, request_uri=request_uri, query=query, base_url=normalized_base)


def validate_discovery_candidate(candidate: Mapping[str, Any]) -> None:
    if candidate.get("schema") != DISCOVERY_CANDIDATE_SCHEMA_V1:
        raise ValueError("unsupported discovery candidate schema")
    if candidate.get("provider") != KURATE_PROVIDER:
        raise ValueError("unsupported discovery provider")
    if candidate.get("authority") != DISCOVERY_AUTHORITY:
        raise ValueError("discovery candidate authority must be triage_only")
    paper = candidate.get("paper")
    assessment = candidate.get("assessment")
    provenance = candidate.get("provenance")
    selection = candidate.get("selection")
    if not all(isinstance(item, Mapping) for item in (paper, assessment, provenance, selection)):
        raise ValueError("discovery candidate sections must be objects")
    metrics = assessment.get("metrics_milli")
    if not isinstance(metrics, Mapping) or set(metrics) != set(KURATE_METRICS):
        raise ValueError("discovery candidate metrics are incomplete")
    for key, value in metrics.items():
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 10_000):
            raise ValueError(f"discovery candidate metric {key} is invalid")
    if not isinstance(provenance.get("snapshot_ref"), str) or not provenance["snapshot_ref"].startswith("sha256:"):
        raise ValueError("discovery candidate snapshot_ref is invalid")
    _canonical_bytes(candidate)


def candidate_receipt_ref(candidate: Mapping[str, Any]) -> str:
    validate_discovery_candidate(candidate)
    return _sha256_ref(_canonical_bytes(candidate))


def metric_score(candidate: Mapping[str, Any], metric: str, *, default: float = 0.5) -> float:
    validate_discovery_candidate(candidate)
    value = candidate["assessment"]["metrics_milli"].get(metric)
    if value is None:
        return float(default)
    score = int(value) / 10_000
    return score if math.isfinite(score) else float(default)


__all__ = [
    "DISCOVERY_AUTHORITY",
    "DISCOVERY_CANDIDATE_SCHEMA_V1",
    "KURATE_METRICS",
    "KURATE_PROVIDER",
    "KurateAdapterError",
    "KurateBatch",
    "candidate_receipt_ref",
    "fetch_kurate_candidates",
    "metric_score",
    "normalize_kurate_response",
    "validate_discovery_candidate",
]
