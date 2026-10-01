# Shared memory pilot acceptance — 2026-10-01

The existing private pilot was resumed from PR #15 rather than replaced. The
update keeps its functional core / imperative shell boundary and 17 MCP tools.

## Completed repairs

- Negative-result retrieval now spans every revision. Search matches original
  titles, statements, assumptions, scopes and negative evidence summaries.
  MCP results include the claim revisions needed to interpret each old receipt.
- The interface preserves earlier counterexamples after a claim is corrected,
  showing their original recipe, scope, assumptions and exact receipt. Current
  claim status still depends only on the current revision.
- Current-revision negative evidence flags transitive dependents for review,
  including newly added dependents. It remains unverified evidence and cannot
  change the source claim's checker verdict. Addressing the objection in a new
  source revision and revising each dependent permits review to be cleared.
- Moved the notification container outside the workbench grid. Browser inspection
  found that it consumed a column and displaced the actual research interface.
- Removed generated TypeScript incremental state from tracked source.

## Verified

| Check | Observed result |
| --- | --- |
| Python regression suite with MCP SDK 1.30.0 | 63 passed |
| Hosted Node regression suite | 28 passed |
| TypeScript | `tsc --noEmit` passed |
| Production Worker build | Passed |
| Private Sites publication | Version 2 succeeded with MCP enabled; owner-only audience preserved |
| Diff whitespace | Passed |
| Browser preview | Corrected two-column layout, signed-out state and negative-result navigation inspected |
| Production D1 before update | Three expected tables; no workspaces present |

Source is pinned in `hosted/lib/kernel-pin.ts`; checker bytes are unchanged.
The updated Sites source commit is `4dfa3c83e775c22da4b448619741e67204989d62`.
The GitHub companion source and deployment source have separate Git histories.

## Remaining integration limits

The user installed the Site's Research Kernel plugin during this continuation.
Its data-tool bindings were not exposed to the current execution runner, so no
successful live user-identity call is claimed. The browser preview has no signed-in
account and reports no WebMCP registrations. Authenticated browser writes, real
WebMCP execution and the connected ChatGPT sidebar remain unverified. Registry
contract tests are not a substitute for these checks.

After the connected tools are available, the acceptance sequence is:

1. Call `rk_workspaces_list` under the authenticated account.
2. Create a private workspace with a UUID request ID.
3. Add the square-of-a-sum example over `x,y = -5..5`, then run `rk_check`.
   Expect 121/121 cases passed and an exact revision-bound receipt.
4. Revise the recipe to omit `2*x*y` and run it. Expect a counterexample.
5. Correct the recipe, check again, and retrieve the old result through
   `rk_negative_memory`. Its receipt must still reference the failed revision.
6. Inspect the same workspace in the ChatGPT panel. Check that selecting a claim
   displays its scope and receipts and that a check updates the workspace.

Use synthetic arithmetic for acceptance. No real research finding, public
publication, invitation, billing charge or transferable token was created by
this validation. Paid services, independent experimental/formal verification and
federation remain separate work beyond this private pilot.
