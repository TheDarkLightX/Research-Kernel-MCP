import { createWorkspace, current, type ClaimInput, type Command } from "./core/model";
import { transition } from "./core/transition";
import { sha256 } from "./hash";
import { CHECKER_SOURCE_SHA256 } from "./checker-pin";

// Public, synthetic teaching data. No database, request identity, or persistence.
// Receipts are produced by the same functional core as real workspace checks.
export function createExampleMemory() {
  const actor = { userId: "example-author", name: "Example author", email: "example@example.test" };
  let state = createWorkspace("example-memory", "Arithmetic examples", actor);
  let step = 0;
  const apply = (command: Command, id: string) => {
    const decision = transition(state, command, { actor, id, now: `2026-10-01T08:${String(step++).padStart(2, "0")}:00.000Z`, checkerSourceHash: CHECKER_SOURCE_SHA256 }, sha256);
    if (decision.decision === "reject") throw new Error(decision.message);
    state = decision.state;
  };
  const target = (id: string) => ({ claimId: id, expectedHash: current(state.claims.find(c => c.id === id)!).hash });
  const square: ClaimInput = {
    title: "Square of a sum", kind: "bounded", statement: "(x + y)² = x² + y² for every tested integer pair.",
    assumptions: "Exact integer arithmetic.", scope: "Integers x and y from −5 to 5, inclusive. No claim outside this finite grid.", dependencies: [],
    recipe: { checker: "integer-grid/v1", variables: { x: { min: -5, max: 5 }, y: { min: -5, max: 5 } }, left: "(x+y)^2", right: "x^2+y^2" },
  };
  apply({ type: "addClaim", claim: square }, "example-square");
  apply({ type: "checkClaim", ...target("example-square") }, "example-square-failed");
  apply({ type: "addClaim", claim: { ...square, title: "Reuse the expansion in a polynomial rewrite", statement: "A rewrite using the square-of-a-sum expansion preserves the polynomial’s value.", kind: "hypothesis", recipe: null, dependencies: ["example-square"] } }, "example-rewrite");
  apply({ type: "reviseClaim", ...target("example-square"), claim: { ...square, statement: "(x + y)² = x² + 2xy + y² for every tested integer pair.", recipe: { ...square.recipe!, right: "x^2+2*x*y+y^2" } } }, "example-square-revised");
  apply({ type: "checkClaim", ...target("example-square") }, "example-square-passed");
  apply({ type: "addClaim", claim: { ...square, title: "Difference of two squares", statement: "(x + y)(x − y) = x² − y² for every tested integer pair.", recipe: { ...square.recipe!, left: "(x+y)*(x-y)", right: "x^2-y^2" } } }, "example-difference");
  apply({ type: "checkClaim", ...target("example-difference") }, "example-difference-passed");
  apply({ type: "addClaim", claim: { ...square, title: "Every integer is its own square", statement: "x² = x for every tested integer.", scope: "Integers x from −5 to 5, inclusive.", recipe: { checker: "integer-grid/v1", variables: { x: { min: -5, max: 5 } }, left: "x^2", right: "x" } } }, "example-idempotent");
  apply({ type: "checkClaim", ...target("example-idempotent") }, "example-idempotent-failed");
  return state;
}
