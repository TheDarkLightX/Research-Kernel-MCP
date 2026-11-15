import copy
import asyncio
import json
from pathlib import Path
import pytest
from internal.research_kernel_mcp.kernel import ResearchKernel
from internal.research_kernel_mcp.shared_memory import export_scoped_claim, import_evidence_package, validate_package


def test_installed_mcp_sdk_discovers_shared_memory_bridge_tools():
    from internal.research_kernel_mcp import server
    assert server.mcp is not None, "The supported MCP SDK must provide FastMCP."
    tools = asyncio.run(server.mcp.list_tools())
    assert {"rk_export_scoped_claim", "rk_import_evidence_package"} <= {tool.name for tool in tools}


def package():
    return json.loads((Path(__file__).parents[1] / "shared-package.json").read_text())


def test_selected_export_omits_private_metadata_and_local_authority(tmp_path):
    kernel = ResearchKernel(tmp_path)
    run = kernel.start_run(goal="Research", title="Research")["run"]["id"]
    atom = kernel.atom_add(run_id=run, atom_type="CLAIM", content="A selected research assertion.", status="SUPPORTED", confidence=0.99, metadata={"private_search_trace": "do not export"})["atom"]
    out = export_scoped_claim(kernel, atom_id=atom["id"], title="Selected assertion", assumptions="Finite domain", scope="A declared finite domain.")
    assert out["authority"] == "unverified"
    assert out["command"]["claim"]["recipe"] is None
    assert "private_search_trace" not in json.dumps(out)
    assert "SUPPORTED" not in json.dumps(out)
    assert "confidence" not in out["command"]["claim"]


def test_typescript_golden_package_is_accepted_as_triage_only_and_idempotent(tmp_path):
    packet = package()
    validate_package(packet)
    kernel = ResearchKernel(tmp_path)
    run = kernel.start_run(goal="External memory", title="External memory")["run"]["id"]
    result = import_evidence_package(kernel, run_id=run, packet=packet)
    assert result["created"] is True
    assert result["atom"]["status"] == "CANDIDATE"
    assert result["atom"]["metadata"]["authority"] == "triage_only"
    assert result["atom"]["evidence_score"] == 0.0
    assert result["atom"]["metadata"]["shared_memory"]["packet"]["receipts"][0]["result"]["cases"] == 121
    again = import_evidence_package(kernel, run_id=run, packet=packet)
    assert again["created"] is False
    assert again["atom"]["id"] == result["atom"]["id"]
    promotion = kernel.promote(claim_atom_id=result["atom"]["id"], to_status="SUPPORTED", rationale="External package was checked.", checks={"replay_recipe": "external"})
    assert promotion["ok"] is False
    assert "has_claim_authority" in promotion["gate"]["missing"]


def test_tampered_and_revoked_packages_fail_before_any_write(tmp_path):
    kernel = ResearchKernel(tmp_path)
    run = kernel.start_run(goal="Reject tampering", title="Reject tampering")["run"]["id"]
    for change in ("statement", "receipt", "revoked"):
        packet = copy.deepcopy(package())
        if change == "statement":
            packet["claim"]["statement"] += " Altered."
        elif change == "receipt":
            packet["receipts"][0]["result"]["cases"] = 0
        else:
            packet["revoked"] = True
        with pytest.raises(ValueError):
            import_evidence_package(kernel, run_id=run, packet=packet)
    assert sum(kernel.run_summary(run)["counts_by_status"].values()) == 0


def test_export_rejects_unsupported_or_excessive_checker_recipe(tmp_path):
    kernel = ResearchKernel(tmp_path)
    run = kernel.start_run(goal="Recipe bounds", title="Recipe bounds")["run"]["id"]
    atom = kernel.atom_add(run_id=run, atom_type="CLAIM", content="Finite claim.")["atom"]
    recipe = package()["claim"]["recipe"]
    with pytest.raises(ValueError):
        export_scoped_claim(kernel, atom_id=atom["id"], title="Invalid category", assumptions="", scope="Finite domain", kind="formal", recipe=recipe)
    recipe["variables"]["x"]["max"] = 100000
    with pytest.raises(ValueError):
        export_scoped_claim(kernel, atom_id=atom["id"], title="Oversized grid", assumptions="", scope="Finite domain", kind="bounded", recipe=recipe)
