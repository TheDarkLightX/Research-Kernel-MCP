"""Optional semantic retrieval adapter. It never mutates research atoms or edges."""
from __future__ import annotations

import os
import uuid

from .client import Client, JevError, MODEL, RESERVE_USD, digest, encode, save_json
from .research import (MAX_OUTPUT_BYTES, _no_symlinks, compose, context_closure,
                       evaluate, lexical, make_plan, normalise_snapshot)


def search(kernel, *, run_id, query, mode="preview", top=3, anchors=()):
    if mode not in {"preview", "cached", "live"}:
        raise JevError("mode must be preview, cached or live")
    if type(top) is not int or not 1 <= top <= 20:
        raise JevError("top must be 1..20")
    allowed = {s.strip() for s in os.environ.get("RK_JEV_ALLOWED_RUNS", "").split(",") if s.strip()}
    if mode == "live" and run_id not in allowed:
        raise JevError("live export requires this exact run ID in RK_JEV_ALLOWED_RUNS; preview the packet first")
    corpus = normalise_snapshot(kernel.graph(run_id))
    context_closure(corpus, anchors)
    plans = make_plan(corpus, query)
    root = kernel.home / "jev-search" / digest(run_id.encode())
    _no_symlinks(root)
    root.mkdir(parents=True, exist_ok=True)
    fingerprint = digest(encode({"snapshot": corpus["snapshot_sha256"], "query": query,
                                 "top": top, "anchors": sorted(anchors)}))
    if mode == "preview":
        packet = {"destination": "https://api.typesafe.ai/v1/systemone",
                  "requests": [{"model": MODEL, **p} for p in plans]}
        preview = root / ("preview-" + fingerprint + ".json")
        save_json(preview, packet)
        out = {"ok": True, "mode": "preview", "authority": "reading_aid_only", "network_calls": 0,
               "run_id": run_id, "snapshot_sha256": corpus["snapshot_sha256"],
               "records": len(corpus["records"]), "requests_before_cache": len(plans),
               "maximum_reserved_usd_before_cache": str(len(plans) * RESERVE_USD),
               "lexical_baseline_ids": lexical(corpus, query, top),
               "export_preview_path": str(preview), "export_sha256": digest(encode(packet)),
               "live_enabled_for_run": run_id in allowed}
    else:
        client = Client(root / "api", max_requests=128, budget_usd="0.25") if mode == "live" else None
        result = evaluate(plans, root / "cache", client=client)
        out = compose(corpus, query, result["scores"], top=top, anchors=anchors)
        receipt = root / ("result-" + fingerprint + "-" + uuid.uuid4().hex + ".json")
        save_json(receipt, {"output": out, "diagnostics": result})
        out["measurement"] = {k: result[k] for k in ("live_calls", "cache_hits", "new_input_tokens", "estimated_new_cost_usd", "elapsed_seconds")}
        out["receipt_path"] = str(receipt)
        out["ok"] = True
    if len(encode(out)) > MAX_OUTPUT_BYTES:
        raise JevError("final output exceeds budget; full local receipt preserved")
    return out
