import asyncio
import json

import pytest

from internal.research_kernel_mcp.kernel import ResearchKernel
from internal.research_kernel_mcp.jev_search import adapter
from internal.research_kernel_mcp.jev_search.client import JevError


def seeded(tmp_path):
    kernel = ResearchKernel(tmp_path / "vault")
    kernel.start_run(goal="synthetic test", run_id="demo")
    kernel.atom_add(run_id="demo", atom_type="CLAIM", content="The motor rotates.", atom_id="motor")
    return kernel


def test_preview_needs_no_key_and_does_not_change_research(tmp_path, monkeypatch):
    kernel = seeded(tmp_path)
    before = kernel.graph("demo")
    events = kernel.event_log_path.read_bytes()
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("RK_JEV_ALLOWED_RUNS", raising=False)
    out = adapter.search(kernel, run_id="demo", query="rotation")
    assert out["network_calls"] == 0 and out["mode"] == "preview"
    assert kernel.graph("demo") == before and kernel.event_log_path.read_bytes() == events
    assert out["live_enabled_for_run"] is False


def test_live_export_is_run_scoped(tmp_path, monkeypatch):
    kernel = seeded(tmp_path)
    monkeypatch.setenv("RK_JEV_ALLOWED_RUNS", "different")
    with pytest.raises(JevError, match="exact run ID"):
        adapter.search(kernel, run_id="demo", query="q", mode="live")


def test_cached_missing_does_not_fall_back_to_network(tmp_path):
    kernel = seeded(tmp_path)
    with pytest.raises(JevError, match="cache miss"):
        adapter.search(kernel, run_id="demo", query="q", mode="cached")


def test_mcp_tool_preview_and_errors(tmp_path, monkeypatch):
    from internal.research_kernel_mcp import server
    kernel = seeded(tmp_path)
    monkeypatch.setattr(server, "_kernel", lambda: kernel)
    result = json.loads(asyncio.run(server.rk_semantic_search(None, "demo", "rotation")))
    assert result["mode"] == "preview" and result["network_calls"] == 0
    bad = json.loads(asyncio.run(server.rk_semantic_search(None, "demo", "q", anchor_ids_json='[1]')))
    assert bad["ok"] is False and bad["authority"] == "none"


def test_graph_and_claim_status_unchanged_with_stubbed_live(tmp_path, monkeypatch):
    kernel = seeded(tmp_path)
    before = kernel.graph("demo")
    monkeypatch.setenv("RK_JEV_ALLOWED_RUNS", "demo")
    monkeypatch.setattr(adapter, "evaluate", lambda *a, **k: {
        "scores": {"motor": .8}, "live_calls": 1, "cache_hits": 0,
        "new_input_tokens": 1, "estimated_new_cost_usd": "0.000000042", "elapsed_seconds": 0})
    result = adapter.search(kernel, run_id="demo", query="rotation", mode="live")
    assert result["lead_ids"] == ["motor"] and kernel.graph("demo") == before
