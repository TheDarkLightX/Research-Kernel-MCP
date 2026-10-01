import test from "node:test";
import assert from "node:assert/strict";
import { registerResearchTools } from "../lib/webmcp";
import { createWorkspace, current } from "../lib/core/model";
import { transition } from "../lib/core/transition";
import { sha256 } from "../lib/hash";
import { CHECKER_SOURCE_SHA256 } from "../lib/checker-pin";
import { owner, input } from "./fixtures";
test("WebMCP registry contracts use the same claim and checker actions and reject bad inputs", async () => {
  const tools = new Map<string, any>(), signals: AbortSignal[] = [];
  (globalThis as any).document = { modelContext: { registerTool: (tool: any, options: any) => { tools.set(tool.name, tool); signals.push(options.signal); } } };
  let w = createWorkspace("web", "Web fixtures", owner), selected = "";
  const add = transition(w, { type: "addClaim", claim: input }, { actor: owner, now: "2026-10-01T00:00:00Z", id: "claim", checkerSourceHash: CHECKER_SOURCE_SHA256 }, sha256);
  if (add.decision !== "accept") throw new Error(); w = add.state;
  const cleanup = registerResearchTools({ read: () => w, select: id => { if (!w.claims.some(c => c.id === id)) throw new Error("Unknown claim."); selected = id; }, execute: async command => {
    const result = transition(w, command, { actor: owner, now: "2026-10-01T00:00:00Z", id: "check", checkerSourceHash: CHECKER_SOURCE_SHA256 }, sha256);
    if (result.decision !== "accept") throw new Error(result.message); w = result.state; return { revision: w.revision };
  } });
  assert.deepEqual([...tools.keys()], ["read_research_memory", "open_research_claim", "run_bounded_research_check"]);
  assert.equal(tools.get("read_research_memory").annotations.readOnlyHint, true);
  tools.get("open_research_claim").execute({ claimId: "claim" }); assert.equal(selected, "claim");
  await tools.get("run_bounded_research_check").execute({ claimId: "claim", expectedHash: current(w.claims[0]).hash });
  assert.equal(tools.get("read_research_memory").execute({}).claims[0].status, "bounded-checked"); const revision = w.revision;
  await assert.rejects(tools.get("run_bounded_research_check").execute({ claimId: "claim", expectedHash: "bad" }));
  assert.equal(w.revision, revision); assert.throws(() => tools.get("read_research_memory").execute({ unexpected: true }));
  cleanup?.(); assert(signals.every(s => s.aborted)); delete (globalThis as any).document;
});
