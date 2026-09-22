"""Bounded live HTTP client with exact usage accounting and no implicit retries."""
from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import stat
import tempfile
import time
from urllib import error, request

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"
MAX_REQUEST_BYTES = 48 * 1024
MAX_RESPONSE_BYTES = 128 * 1024
MAX_INPUT_TOKENS = 65536
PRICE_PER_MILLION = Decimal("0.042")
RESERVE_USD = Decimal(MAX_INPUT_TOKENS) * PRICE_PER_MILLION / 1_000_000
DEFAULT_KEY_FILE = Path.home() / ".config/secrets/typesafe.env"


class JevError(ValueError):
    """Messages are safe to print; never include provider bodies or credentials."""


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_key(path=None):
    if os.environ.get("TYPESAFE_API_KEY"):
        return os.environ["TYPESAFE_API_KEY"].strip()
    source = Path(path) if path else DEFAULT_KEY_FILE
    try:
        info = source.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
            raise JevError("credential file must be an owner-only regular file")
        if info.st_size > 16384:
            raise JevError("credential file exceeds size limit")
        matches = re.findall(r"^\s*(?:export\s+)?TYPESAFE_API_KEY\s*=\s*(.*?)\s*$",
                             source.read_text(), re.MULTILINE)
        if len(matches) != 1 or "$" in matches[0] or "`" in matches[0]:
            raise JevError("expected one literal TYPESAFE_API_KEY assignment")
        words = shlex.split(matches[0], comments=True)
        if len(words) != 1 or not words[0]:
            raise JevError("empty or invalid credential assignment")
        return words[0]
    except (OSError, UnicodeError) as exc:
        raise JevError("TypeSafe credential is unavailable") from None


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise JevError("redirect rejected")


def post(body, key):
    req = request.Request(ENDPOINT, data=body, method="POST",
                          headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with request.build_opener(NoRedirect).open(req, timeout=30) as response:
            data = response.read(MAX_RESPONSE_BYTES + 1)
    except error.HTTPError as exc:
        raise JevError(f"TypeSafe HTTP {exc.code}; no automatic retry") from None
    except (error.URLError, TimeoutError, OSError):
        raise JevError("TypeSafe transport failed; billing unknown; no automatic retry") from None
    if len(data) > MAX_RESPONSE_BYTES:
        raise JevError("response exceeded size limit")
    return data


def probability(x):
    return type(x) in (int, float) and 0 <= x <= 1 and math.isfinite(x)


def validate_response(response, questions):
    if not isinstance(response, dict) or response.get("model") != MODEL:
        raise JevError("response model does not match pinned model")
    usage = response.get("usage")
    if not isinstance(usage, dict) or any(type(usage.get(k)) is not int or usage[k] < 0
                                           for k in ("input_tokens", "output_tokens")):
        raise JevError("invalid token usage")
    if usage["input_tokens"] > MAX_INPUT_TOKENS:
        raise JevError("reported usage exceeded documented context allowance")
    answers = response.get("answers")
    if not isinstance(answers, dict) or set(answers) != set(questions):
        raise JevError("response question IDs do not match request")
    for key, question in questions.items():
        answer = answers[key]
        kind = question["type"]
        if not isinstance(answer, dict) or answer.get("type") != kind:
            raise JevError("answer type mismatch")
        if kind == "noul":
            if set(answer) != {"type", "noul"} or not probability(answer.get("noul")):
                raise JevError("invalid Noul answer")
        elif kind == "choice":
            if set(answer) != {"type", "choice", "confidence", "probabilities"}:
                raise JevError("unexpected Choice fields")
            probs = answer.get("probabilities")
            if (not isinstance(probs, dict) or set(probs) != set(question["criteria"])
                    or any(not probability(v) for v in probs.values())
                    or abs(math.fsum(probs.values()) - 1) > 1e-5
                    or not probability(answer.get("confidence"))
                    or answer.get("choice") not in probs
                    or probs[answer["choice"]] < max(probs.values()) - 1e-5):
                raise JevError("invalid Choice distribution")
        else:
            raise JevError("unsupported answer type")
    return response


def save_bytes(path, data):
    path = Path(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, mode="wb", delete=False) as f:
        name = f.name
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(name, path)


def save_json(path, value):
    save_bytes(path, encode(value) + b"\n")


class Client:
    def __init__(self, run_dir, *, key_file=None, max_requests=16, budget_usd="0.05",
                 transport=post, key_loader=load_key):
        self.root = Path(run_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.key_file, self.transport, self.key_loader = key_file, transport, key_loader
        self.max_requests, self.budget = max_requests, Decimal(str(budget_usd))
        if type(max_requests) is not int or max_requests < 1 or not self.budget.is_finite() or self.budget <= 0:
            raise JevError("invalid request budget")

    @contextmanager
    def locked_ledger(self):
        with (self.root / "ledger.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            p = self.root / "ledger.json"
            data = json.loads(p.read_text()) if p.exists() else {"calls": [], "model": MODEL}
            if data.get("model") != MODEL:
                raise JevError("ledger model mismatch")
            yield data
            save_json(p, data)

    def evaluate(self, state, questions):
        if not questions or len(questions) > 32:
            raise JevError("request needs 1..32 questions")
        body = encode({"model": MODEL, "state": state, "questions": questions})
        if len(body) > MAX_REQUEST_BYTES:
            raise JevError("request exceeded byte cap")
        key = self.key_loader(self.key_file)
        if not key or key.encode() in body:
            raise JevError("empty credential or credential included in request")
        with self.locked_ledger() as ledger:
            spent = sum((Decimal(c["accounted_usd"]) for c in ledger["calls"]), Decimal(0))
            if len(ledger["calls"]) >= self.max_requests or spent + RESERVE_USD > self.budget:
                raise JevError("request or spending allowance exhausted")
            number = len(ledger["calls"]) + 1
            record = {"number": number, "request_sha256": digest(body), "status": "reserved",
                      "accounted_usd": str(RESERVE_USD), "price_per_million_input": str(PRICE_PER_MILLION)}
            ledger["calls"].append(record)
        stem = self.root / f"request-{number:03d}"
        save_json(stem.with_suffix(".json"), json.loads(body))
        started = time.perf_counter()
        response_hash = None
        try:
            raw = self.transport(body, key)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise JevError("response exceeded byte cap")
            if key.encode() in raw:
                raise JevError("credential detected in response; refusing to persist it")
            # Keep the wire bytes even when schema validation fails. A later
            # stochastic response cannot explain a discarded earlier failure.
            response_hash = digest(raw)
            save_bytes(stem.with_suffix(".response.raw.json"), raw)
            response = validate_response(json.loads(raw), questions)
            cost = Decimal(response["usage"]["input_tokens"]) * PRICE_PER_MILLION / 1_000_000
            update = {"status": "ok", "accounted_usd": str(cost), "usage": response["usage"],
                      "model": response["model"], "elapsed_seconds": time.perf_counter() - started,
                      "response_sha256": response_hash, "request_bytes": len(body)}
            save_json(stem.with_suffix(".response.json"), response)
        except Exception as exc:
            update = {"status": "failed", "elapsed_seconds": time.perf_counter() - started,
                      "failure_type": type(exc).__name__, "billing": "unknown_reservation_retained"}
            if response_hash is not None:
                update["response_sha256"] = response_hash
            with self.locked_ledger() as ledger:
                ledger["calls"][number - 1].update(update)
            if isinstance(exc, JevError):
                raise
            raise JevError("invalid or unavailable response; reservation retained") from None
        with self.locked_ledger() as ledger:
            ledger["calls"][number - 1].update(update)
        return {"response": response, "receipt": dict(record, **update)}
