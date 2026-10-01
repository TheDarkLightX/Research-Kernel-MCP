import test from "node:test";
import assert from "node:assert/strict";
import { createExampleMemory } from "../lib/example-memory";
import { canonical, claimStatus, current, hasFailureHistory } from "../lib/core/model";
import { checkRecipe } from "../lib/core/checker";
import { sha256 } from "../lib/hash";

test("the public teaching example contains replayable receipts and preserves the failed revision", () => {
  const workspace = createExampleMemory();
  const square = workspace.claims.find(c => c.id === "example-square")!;
  assert.equal(current(square).number, 2);
  assert.equal(claimStatus(workspace, square), "bounded-checked");
  assert(hasFailureHistory(workspace, square));
  assert.equal(workspace.claims.filter(c => c.needsReview).length, 1);
  for (const receipt of workspace.receipts) {
    const revision = workspace.claims.find(c => c.id === receipt.claimId)!.revisions.find(r => r.hash === receipt.claimRevision)!;
    assert.deepEqual(receipt.result, checkRecipe(revision.recipe!, sha256));
    assert.equal(receipt.recipeHash, sha256(canonical(revision.recipe)));
    assert.equal(receipt.transcriptHash, sha256(canonical(receipt.result)));
  }
  assert.equal(canonical(workspace), canonical(createExampleMemory()));
  assert.equal(workspace.publications.length, 0);
});
