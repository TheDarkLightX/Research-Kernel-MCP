import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { checkRecipe, type Recipe } from "../lib/core/checker";
import { canonical, current, createWorkspace, claimStatus, type Workspace, type Actor, type Context, type Command, type ClaimInput } from "../lib/core/model";
import { transition, publicationDigest } from "../lib/core/transition";
import { sha256 } from "../lib/hash";
import { CHECKER_SOURCE_SHA256 } from "../lib/checker-pin";
import { owner, editor, reader, recipe, input } from "./fixtures";
function context(id: string, actor = owner): Context { return { id, actor, now: "2026-10-01T00:00:00.000Z", checkerSourceHash: CHECKER_SOURCE_SHA256 }; }
function apply(s: Workspace, cmd: Command, id: string, actor = owner) { const d = transition(s, cmd, context(id, actor), sha256); assert.equal(d.decision, "accept", JSON.stringify(d)); if (d.decision !== "accept") throw new Error(); return d.state; }
function base() { return apply(createWorkspace("w", "Lab", owner), { type: "addClaim", claim: input }, "a"); }
test("finite checker enumerates the complete domain using exact integers", () => {
  const r = checkRecipe(recipe, sha256); assert.equal(r.outcome, "passed"); assert.equal(r.cases, 121); assert.equal(r.totalCases, 121); assert.equal(r.counterexample, null);
});
test("counterexample is deterministic and replayable", () => {
  const r = checkRecipe({ ...recipe, right: "x^2+y^2" }, sha256); assert.equal(r.outcome, "counterexample"); assert.deepEqual(r.counterexample, { inputs: { x: -5, y: -5 }, left: "100", right: "50" }); assert.deepEqual(checkRecipe({ ...recipe, right: "x^2+y^2" }, sha256), r);
});
test("inconclusive results never turn unsupported syntax or resource overruns into passes", () => {
  for (const bad of [{ ...recipe, left: "sin(x)" }, { ...recipe, left: "x%0" }, { ...recipe, left: "x^9" }, { ...recipe, variables: { x: { min: 0, max: 10000 } } }, { ...recipe, left: "(".repeat(60) + "x" + ")".repeat(60) }]) assert.equal(checkRecipe(bad, sha256).outcome, "inconclusive");
  assert.equal(checkRecipe({ ...recipe, left: "-x^2", right: "0-x*x" }, sha256).outcome, "passed");
});
test("checker provenance matches exact checked-in source bytes", () => { assert.equal(sha256(readFileSync("lib/core/checker.ts", "utf8")), CHECKER_SOURCE_SHA256); });
test("functional core rejects without mutation and replay is byte-identical", () => {
  const w = base(), before = canonical(w), cmd: Command = { type: "checkClaim", claimId: "a", expectedHash: current(w.claims[0]).hash };
  const a = transition(w, cmd, context("check"), sha256), b = transition(w, cmd, context("check"), sha256); assert.equal(canonical(a), canonical(b)); assert.equal(canonical(w), before);
  const bad = transition(w, { ...cmd, expectedHash: "0".repeat(64) }, context("bad"), sha256); assert.equal(bad.decision, "reject"); assert.equal(canonical(w), before);
});
test("strict admission rejects caller-injected authority and invalid category recipes", () => {
  const w = base();
  assert.equal(transition(w, { type: "checkClaim", claimId: "a", expectedHash: current(w.claims[0]).hash, authority: "formal-proof" }, context("bad"), sha256).decision, "reject");
  assert.equal(transition(w, { type: "addClaim", claim: { ...input, kind: "formal" } }, context("bad"), sha256).decision, "reject");
});
test("workspace roles apply to core transitions and publication", () => {
  let w = base(); w.members.push({ ...reader, role: "reader" }, { ...editor, role: "editor" });
  const command: Command = { type: "checkClaim", claimId: "a", expectedHash: current(w.claims[0]).hash };
  for (const actor of [reader, { ...reader, userId: "outsider" }]) assert.equal(transition(w, command, context("x", actor), sha256).decision, "reject");
  w = apply(w, command, "editor-check", editor); assert.equal(claimStatus(w, w.claims[0]), "bounded-checked");
  assert.equal(transition(w, { ...command, type: "publishClaim" }, context("x", editor), sha256).decision, "reject");
});
test("evidence type and user-declared hashes do not authorize checks", () => {
  let w = apply(createWorkspace("w", "Lab", owner), { type: "addClaim", claim: { ...input, kind: "formal", recipe: null } }, "f");
  w = apply(w, { type: "attachEvidence", claimId: "f", expectedHash: current(w.claims[0]).hash, kind: "formal", uri: "https://example.test/proof", summary: "Caller claims a proof passed.", artifactHash: "a".repeat(64) }, "e");
  assert.equal(claimStatus(w, w.claims[0]), "unverified"); assert.equal(transition(w, { type: "checkClaim", claimId: "f", expectedHash: current(w.claims[0]).hash }, context("c"), sha256).decision, "reject");
});
test("revision and failed dependencies invalidate transitive dependents without deleting evidence", () => {
  let w = base();
  w = apply(w, { type: "checkClaim", claimId: "a", expectedHash: current(w.claims[0]).hash }, "check");
  w = apply(w, { type: "addClaim", claim: { ...input, title: "Dependent", dependencies: ["a"] } }, "b");
  w = apply(w, { type: "addClaim", claim: { ...input, title: "Transitive", dependencies: ["b"] } }, "c");
  const old = current(w.claims[0]).hash;
  w = apply(w, { type: "reviseClaim", claimId: "a", expectedHash: old, claim: { ...input, recipe: { ...recipe, right: "x^2+y^2" } } }, "revise");
  assert.equal(w.claims[1].needsReview, true); assert.equal(w.claims[2].needsReview, true); assert.equal(w.receipts[0].claimRevision, old); assert.equal(claimStatus(w, w.claims[0]), "unverified");
  w = apply(w, { type: "checkClaim", claimId: "a", expectedHash: current(w.claims[0]).hash }, "negative");
  assert.equal(claimStatus(w, w.claims[0]), "counterexample");
  w = apply(w, { type: "reviseClaim", claimId: "b", expectedHash: current(w.claims[1]).hash, claim: { ...input, title: "Dependent", dependencies: ["a"] } }, "review");
  assert.equal(w.claims[1].needsReview, true, "revising cannot waive a failed dependency");
});
test("dependency cycles are rejected", () => { let w = base(); w = apply(w, { type: "addClaim", claim: { ...input, dependencies: ["a"] } }, "b"); assert.equal(transition(w, { type: "reviseClaim", claimId: "a", expectedHash: current(w.claims[0]).hash, claim: { ...input, dependencies: ["b"] } }, context("cycle"), sha256).decision, "reject"); });
test("contribution points are deduplicated, non-transferable and outcome neutral", () => {
  let w = base(); const cmd: Command = { type: "checkClaim", claimId: "a", expectedHash: current(w.claims[0]).hash };
  w = apply(w, cmd, "c1"); w = apply(w, cmd, "c2"); assert.equal(w.ledger.length, 1); assert.equal(w.ledger[0].transferable, false); assert.equal(w.usage.checks, 2);
  w = apply(w, { type: "addClaim", claim: { ...input, recipe: { ...recipe, right: "x^2+y^2" } } }, "bad");
  w = apply(w, { type: "checkClaim", claimId: "bad", expectedHash: current(w.claims[1]).hash }, "c3"); assert.equal(w.ledger[1].points, w.ledger[0].points); assert.equal(w.ledger[1].reason, "counterexample");
});
test("selected publication excludes identities and importing never transfers verification authority", () => {
  let w = base(); w = apply(w, { type: "checkClaim", claimId: "a", expectedHash: current(w.claims[0]).hash }, "check");
  w = apply(w, { type: "publishClaim", claimId: "a", expectedHash: current(w.claims[0]).hash }, "pub");
  const packet = w.publications[0]; assert.equal(publicationDigest(packet, sha256), packet.hash); assert.equal(packet.claim.author, "contributor"); assert.equal(packet.receipts[0].requestedBy, "contributor"); assert(!canonical(packet).includes(owner.email));
  const imported = apply(createWorkspace("other", "Other lab", editor), { type: "importPackage", packet }, "import", editor);
  assert.equal(imported.receipts.length, 0); assert.equal(claimStatus(imported, imported.claims[0]), "unverified"); assert.equal(imported.evidence[0].authority, "unverified");
  const tampered = structuredClone(packet); tampered.claim.statement = "Modified assertion."; assert.equal(transition(imported, { type: "importPackage", packet: tampered }, context("bad", editor), sha256).decision, "reject");
  const rebound = structuredClone(packet); rebound.receipts[0].claimId = "other"; rebound.hash = publicationDigest(rebound, sha256); assert.equal(transition(imported, { type: "importPackage", packet: rebound }, context("bad", editor), sha256).decision, "reject");
});
test("email invitation acceptance binds the verified account identity", () => {
  let w = apply(base(), { type: "invite", email: "Reader@example.test", role: "reader" }, "invite");
  assert.equal(transition(w, { type: "join" }, context("wrong", { ...reader, email: "other@example.test" }), sha256).decision, "reject");
  w = apply(w, { type: "join" }, "join", reader); assert.equal(w.members.find(m => m.userId === reader.userId)?.role, "reader"); assert.equal(w.invitations.length, 0);
});
