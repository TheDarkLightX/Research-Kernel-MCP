"""Search contract witnesses; model accuracy is tested separately against live Jev."""
import copy
import json
from pathlib import Path

import pytest

from internal.research_kernel_mcp.jev_search.client import Client, JevError, MODEL, encode
from internal.research_kernel_mcp.jev_search import research as s


def graph():
    def atom(i, content, kind="RESULT"):
        return {"id": i, "run_id": "run", "content": content, "type": kind,
                "status": "CANDIDATE", "tags": [], "source_refs": [], "artifact_refs": []}
    return {"run_id": "run", "atoms": [
        atom("claim", "The stock exchange discount guarantees a profit.", "CLAIM"),
        atom("loss", "Delivery took several sessions and the stock price fell.", "COUNTEREXAMPLE"),
        atom("fix", "Correction: claim remains a hypothesis, not a proven strategy."),
        atom("other", "The laboratory centrifuge runs at 1000 rpm.")],
        "edges": [{"source_atom_id": "loss", "target_atom_id": "claim", "edge_type": "REFUTES"}]}


def corpus():
    return s.normalise_snapshot(graph())


def fake_client(tmp_path, values=None):
    calls = []
    def transport(body, key):
        request = json.loads(body)
        calls.append(request)
        answers = {qid: {"type": "noul", "noul": (values or {}).get(record["id"], 0.0)}
                   for qid, record in zip(request["questions"], request["state"]["records"])}
        return encode({"model": MODEL, "answers": answers,
                       "usage": {"input_tokens": 100, "output_tokens": 0}})
    return Client(tmp_path / "api", transport=transport, key_loader=lambda _: "synthetic-credential"), calls


def test_full_scan_includes_zero_lexical_match():
    plan = s.make_plan(corpus(), "Where did shares sink during the wait?")
    assert set(r["id"] for p in plan for r in p["state"]["records"]) == {"claim", "loss", "fix", "other"}


def test_zero_score_counterexample_and_unlinked_correction_retained():
    packet = s.compose(corpus(), "discount", {"claim": .9, "loss": 0, "fix": 0, "other": 0}, top=1)
    assert set(packet["required_ids"]) == {"loss", "fix"}
    assert {r["id"] for r in packet["reading_packet"]} == {"claim", "loss", "fix"}
    assert packet["authority"] == "reading_aid_only"


@pytest.mark.parametrize("punctuation", [":", ".", ",", ")"])
def test_punctuated_correction_reference_is_retained(punctuation):
    raw = graph()
    raw["atoms"][2]["content"] = f"Correction to claim{punctuation} The inference was too broad."
    result = s.compose(s.normalise_snapshot(raw), "q", {"claim": .9, "loss": 0, "fix": 0, "other": 0}, top=1)
    assert "fix" in result["required_ids"]


def test_transitive_dependencies_keep_refutations():
    raw = graph()
    raw["edges"].append({"source_atom_id": "other", "target_atom_id": "claim", "edge_type": "DEPENDS_ON"})
    out = s.compose(s.normalise_snapshot(raw), "anything", {a["id"]: float(a["id"] == "other") for a in raw["atoms"]}, top=1)
    assert "loss" in out["required_ids"]


def test_no_match_and_explicit_anchor():
    values = {i: 0 for i in ("claim", "loss", "fix", "other")}
    assert s.compose(corpus(), "absent", values)["reading_packet"] == []
    out = s.compose(corpus(), "absent", values, anchors=["claim"])
    assert out["lead_ids"] == [] and "loss" in out["required_ids"]
    with pytest.raises(JevError, match="anchor"):
        s.compose(corpus(), "absent", values, anchors=["missing"])


@pytest.mark.parametrize("mutation", ["duplicate", "wrong_run", "dangling", "bad_content", "bad_ref", "secret", "parent"])
def test_invalid_corpus_rejected(mutation):
    raw = graph()
    if mutation == "duplicate": raw["atoms"].append(copy.deepcopy(raw["atoms"][0]))
    if mutation == "wrong_run": raw["atoms"][0]["run_id"] = "another"
    if mutation == "dangling": raw["edges"][0]["target_atom_id"] = "missing"
    if mutation == "bad_content": raw["atoms"][0]["content"] = "x" * 32769
    if mutation == "bad_ref": raw["atoms"][0]["source_refs"] = [42]
    if mutation == "secret": raw["atoms"][0]["content"] = "api_key = superprivate123456"
    if mutation == "parent": raw["atoms"][0]["parent_ids"] = ["absent"]
    with pytest.raises(JevError): s.normalise_snapshot(raw)


def test_record_cap_rejects_instead_of_truncating():
    raw = graph()
    raw["atoms"] = [dict(raw["atoms"][0], id=f"n{i}") for i in range(s.MAX_RECORDS + 1)]
    raw["edges"] = []
    with pytest.raises(JevError, match="record"): s.normalise_snapshot(raw)


def test_empty_graph_is_valid_no_requests():
    g = s.normalise_snapshot({"run_id": "r", "atoms": [], "edges": []})
    assert s.make_plan(g, "anything") == []


def test_json_duplicates_and_symlinks_rejected(tmp_path):
    p = tmp_path / "input.json"
    p.write_text('{"run_id":"r","run_id":"s"}')
    with pytest.raises(JevError): s.load_json(p)
    p.write_text(json.dumps(graph()))
    link = tmp_path / "link.json"
    link.symlink_to(p)
    with pytest.raises(JevError): s.load_json(link)


def test_cache_replays_without_key_or_new_call(tmp_path):
    client, calls = fake_client(tmp_path, {"claim": .9})
    plan = s.make_plan(corpus(), "stock exchange")
    first = s.evaluate(plan, tmp_path / "cache", client=client)
    second = s.evaluate(plan, tmp_path / "cache")
    assert len(calls) == 1 and first["scores"] == second["scores"]
    assert second["live_calls"] == 0 and second["cache_hits"] == 1
    assert second["new_input_tokens"] == 0


def test_changed_content_cache_miss_and_graph_recompose(tmp_path):
    client, calls = fake_client(tmp_path, {"claim": .9})
    g = corpus()
    s.evaluate(s.make_plan(g, "q"), tmp_path / "cache", client=client)
    raw = graph()
    raw["atoms"][0]["content"] += " Changed."
    s.evaluate(s.make_plan(s.normalise_snapshot(raw), "q"), tmp_path / "cache", client=client)
    assert len(calls) == 2
    raw["edges"].append({"source_atom_id": "other", "target_atom_id": "claim", "edge_type": "CONTRADICTS"})
    changed = s.normalise_snapshot(raw)
    run = s.evaluate(s.make_plan(changed, "q"), tmp_path / "cache")
    assert "other" in s.compose(changed, "q", run["scores"])["required_ids"]


def test_corrupt_cache_not_retried(tmp_path):
    client, calls = fake_client(tmp_path)
    plan = s.make_plan(corpus(), "q")
    s.evaluate(plan, tmp_path / "cache", client=client)
    path = next((tmp_path / "cache").glob("*.json"))
    cached = json.loads(path.read_text())
    cached["response"]["answers"]["q000"]["noul"] = .999
    path.write_text(json.dumps(cached))
    with pytest.raises(JevError, match="cache"):
        s.evaluate(plan, tmp_path / "cache", client=client)
    assert len(calls) == 1


def test_budget_preflight_before_network(tmp_path):
    client, calls = fake_client(tmp_path)
    client.max_requests = 1
    g = corpus()
    plans = s.make_plan(g, "q", batch_size=1)
    with pytest.raises(JevError, match="budget"):
        s.evaluate(plans, tmp_path / "cache", client=client)
    assert calls == []


def test_partial_failure_is_error_with_prior_receipt(tmp_path):
    client, calls = fake_client(tmp_path)
    original = client.transport
    def fail_second(body, key):
        if calls: raise JevError("provider unavailable")
        return original(body, key)
    client.transport = fail_second
    with pytest.raises(JevError):
        s.evaluate(s.make_plan(corpus(), "q", batch_size=1), tmp_path / "cache", client=client)
    ledger = json.loads((client.root / "ledger.json").read_text())
    assert [c["status"] for c in ledger["calls"]] == ["ok", "failed"]


def test_missing_score_and_nonfinite_rejected():
    with pytest.raises(JevError): s.compose(corpus(), "q", {"claim": .9})
    with pytest.raises(JevError): s.compose(corpus(), "q", {i: float("nan") for i in ("claim", "loss", "fix", "other")})


def test_required_output_overflow_never_silently_drops():
    scores = {i: .9 for i in ("claim", "loss", "fix", "other")}
    with pytest.raises(JevError, match="output"):
        s.compose(corpus(), "q", scores, output_limit=10)


def test_input_is_not_mutated_and_order_independent():
    raw = graph()
    before = copy.deepcopy(raw)
    a = s.normalise_snapshot(raw)
    raw["atoms"].reverse()
    b = s.normalise_snapshot(raw)
    assert a == b
    assert before["atoms"][0] == raw["atoms"][-1]


def test_batch_wire_budget_including_questions():
    plans = s.make_plan(corpus(), "q", batch_size=2)
    assert all(len(encode({"model": MODEL, **p})) <= s.MAX_PACKET_BYTES for p in plans)
    assert all(len(p["questions"]) <= 2 for p in plans)


def test_fts_handles_punctuation_without_sql_or_fts_injection():
    assert isinstance(s.lexical(corpus(), '" OR *; DROP TABLE atoms --'), list)


def test_exact_content_and_provenance_returned():
    g = graph()
    g["atoms"][0]["artifact_refs"] = ["/tmp/not-opened"]
    c = s.normalise_snapshot(g)
    scores = {i: float(i == "claim") for i in ("claim", "loss", "fix", "other")}
    row = s.compose(c, "q", scores, top=1)["reading_packet"][0]
    assert row["content"] == g["atoms"][0]["content"]
    assert row["artifact_refs"] == ["/tmp/not-opened"]
