import test from "node:test";
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import vm from "node:vm";
import { SqliteD1 } from "./sqlite-d1";
import { owner, reader, input } from "./fixtures";
import { ResearchStore, AppError } from "../lib/store";
import { handleMcp } from "../lib/mcp-handler";
import { toolDiscovery, callResearchTool } from "../lib/mcp-tools";
import { memoryWidget } from "../lib/memory-widget";
function req(method: string, params: unknown = {}, headers: Record<string, string> = {}) {
  return new Request("https://pilot.example.test/mcp", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream", ...headers }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }) });
}
test("stateless MCP initialization negotiates versions and discovery is free of research data", async () => {
  const db = new SqliteD1(), s = new ResearchStore(db.port()), deps = { authenticate: async () => owner, store: () => s };
  const init = await handleMcp(req("initialize", { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "test", version: "1" } }), deps); const v: any = await init.json();
  assert.equal(init.status, 200); assert.equal(v.result.protocolVersion, "2025-06-18");
  const discovery: any = await (await handleMcp(req("tools/list"), deps)).json(); assert.equal(discovery.result.tools.length, 17); assert(!JSON.stringify(discovery).includes(owner.email));
  assert.deepEqual(toolDiscovery().find(t => t.name === "rk_open_memory")!._meta!["openai/ui"].entrypoints, [{ type: "global" }, { type: "thread" }]); db.close();
});
test("missing user identity and unauthorized membership produce HTTP 401/403", async () => {
  const db = new SqliteD1(), s = new ResearchStore(db.port()), w = await s.create("Lab", randomUUID(), owner);
  let r = await handleMcp(req("tools/call", { name: "rk_memory_get", arguments: { workspaceId: w.id } }), { authenticate: async () => { throw new AppError(401, "sign-in-required", "User identity required."); }, store: () => s }); assert.equal(r.status, 401);
  r = await handleMcp(req("tools/call", { name: "rk_memory_get", arguments: { workspaceId: w.id } }), { authenticate: async () => reader, store: () => s }); assert.equal(r.status, 403); db.close();
});
test("tool calls use the same FCIS commit path and fail strict invalid arguments", async () => {
  const db = new SqliteD1(), s = new ResearchStore(db.port()), w = await s.create("Lab", randomUUID(), owner), deps = { authenticate: async () => owner, store: () => s };
  let r: any = await (await handleMcp(req("tools/call", { name: "rk_claim_add", arguments: { workspaceId: w.id, expectedRevision: 0, requestId: randomUUID(), claim: input } }), deps)).json();
  assert.equal(r.result.structuredContent.revision, 1); const cid = r.result.structuredContent.result.claimId;
  r = await (await handleMcp(req("tools/call", { name: "rk_memory_get", arguments: { workspaceId: w.id, claimId: cid } }), deps)).json();
  assert.equal(r.result.structuredContent.claims[0].status, "unverified"); const hash = r.result.structuredContent.claims[0].revisions[0].hash;
  r = await (await handleMcp(req("tools/call", { name: "rk_check", arguments: { workspaceId: w.id, expectedRevision: 1, requestId: randomUUID(), claimId: cid, expectedHash: hash } }), deps)).json();
  assert.equal(r.result.structuredContent.result.receipt.result.cases, 121);
  await assert.rejects(callResearchTool("rk_catalog", { authority: "owner" }, s, reader), e => e instanceof AppError && e.code === "invalid-arguments"); db.close();
});
test("transport rejects invalid origins, versions, malformed messages and unbounded bodies", async () => {
  const db = new SqliteD1(), deps = { authenticate: async () => owner, store: () => new ResearchStore(db.port()) };
  assert.equal((await handleMcp(req("tools/list", {}, { Origin: "https://unrelated.example.test" }), deps)).status, 403);
  assert.equal((await handleMcp(req("ping", {}, { "MCP-Protocol-Version": "wrong" }), deps)).status, 400);
  assert.equal((await handleMcp(new Request("https://pilot.example.test/mcp", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{" }), deps)).status, 400);
  assert.equal((await handleMcp(new Request("https://pilot.example.test/mcp", { method: "POST", headers: { "Content-Type": "application/json" }, body: "x".repeat(250001) }), deps)).status, 413);
  assert.equal((await handleMcp(new Request("https://pilot.example.test/mcp"), deps)).status, 405); db.close();
});
test("MCP App resource has valid script syntax and no preloaded private records", () => {
  const html = memoryWidget("https://pilot.example.test"); const script = html.split("<script>")[1].split("</script>")[0];
  assert.doesNotThrow(() => new vm.Script(script)); assert(!html.includes(owner.email)); assert(html.includes("ui/initialize")); assert(html.includes("tools/call")); assert(html.includes("event") || html.includes("e.source!==window.parent"));
});
