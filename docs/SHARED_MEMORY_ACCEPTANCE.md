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

## Live installed-plugin acceptance — 2026-10-03

Retried against the deployed private Site through the installed Research Kernel
plugin. All 17 tool bindings were exposed. Fifteen calls were recorded, with
their exact arguments, timestamps, structured results and text results; every
call completed without an error. This is live authenticated MCP evidence, not
a replacement for the earlier hosted tests or deployment record.

| Check | Observed result |
| --- | --- |
| `rk_workspaces_list` under the connected account | Passed; initially empty, then the synthetic workspace returned with owner role, one claim and workspace revision 6 |
| Private workspace creation | Passed with a UUID request ID; the private backup contains only one owner and no invitations |
| Initial square-of-a-sum recipe | Passed 121/121 integer pairs for `x,y = -5..5` |
| Recipe revised to `x^2+y^2` | Counterexample on the first tested pair: `x=-5, y=-5`, left `100`, right `50`; 1 case executed from a 121-case grid |
| Cross term restored in claim revision 3 | Passed 121/121; a new receipt binds the corrected revision |
| `rk_negative_memory` after correction | Returned the identical failed-revision receipt, its original recipe/scope and all three claim revisions; current status is `bounded-checked` |
| Independent receipt verification | Passed for all three claim-revision, recipe, checker-source, output-stream and result-transcript fingerprints; independent Python integer arithmetic reproduced every result |
| `rk_memory_get` after correction | Returned the three unchanged receipts at workspace revision 6 |
| `rk_open_memory` data call | Passed; returned the same owner workspace at revision 6; visible ChatGPT panel behavior remains unverified |
| Publication, access and financial boundary | Empty catalog; no workspace publications/invitations; zero package exports; `pilot-no-charges`, `financialValue: none`, two non-transferable contribution records |

The immutable claim contract is: title **Square of a sum**; statement
`(x + y)² = x² + 2xy + y² for each tested integer pair.`; assumption
**Integer arithmetic.**; scope **x and y in −5..5. This check makes no claim
outside that finite grid.** The left recipe is `(x+y)^2`. Revisions 1 and 3
use `x^2+2*x*y+y^2`; revision 2 deliberately omits `2*x*y` while retaining
the same prose contract.

These are the full receipt bindings, excluding account identities and the
private workspace identifier:

```json
[
  {
    "claimRevisionNumber": 1,
    "claimRevision": "39a91457fdfc01365629533424a32deb7df91ef0316cd7fdd61826ed085f85fa",
    "receiptId": "c0e6ee2700b919bdc7d2835828a529120cc5aa24ccb9b47f00c3743a52aa4afa",
    "recipeHash": "8001f1e3c93a92730720011af0f391ac27ed58aedeb0cbb24030983b3698e311",
    "checkerSourceHash": "9fc12f8d3e7fc5f353f40dc8cc3b30a46fb778a02c5e25fdd693bb070bbf0c09",
    "transcriptHash": "ddfe908380cd1f0eb9809099bea1426befaaaea2038a760deb0212d184820d6b",
    "outputsHash": "ac4d80cdb9cdd687d1dae47248762096cfc26842fe9d4d4032a98c9cbb03157f",
    "outcome": "passed",
    "cases": 121,
    "totalCases": 121
  },
  {
    "claimRevisionNumber": 2,
    "claimRevision": "322bf555c0bf62e11ba02738b4c3d199a43239c9f74a672a2b04b39517a9253f",
    "receiptId": "b55e5ea89d4faabeba95640f5cd3c9d6c75752202b2863ebc431c73ad512975e",
    "recipeHash": "78bc40061e44aaad06873e0eefad637da89d0fa3302618855cf85f9ae58e3b78",
    "checkerSourceHash": "9fc12f8d3e7fc5f353f40dc8cc3b30a46fb778a02c5e25fdd693bb070bbf0c09",
    "transcriptHash": "a8306adf6f239a51a131ba3b7a0022477b1e63beb5eaac6f7f793e2d33a9439b",
    "outputsHash": "d233fccee201d9447142bb08022168383d74e3b660170410b1789e1a01f01e6a",
    "outcome": "counterexample",
    "cases": 1,
    "totalCases": 121
  },
  {
    "claimRevisionNumber": 3,
    "claimRevision": "9019a574b8798dbdb1447281730ab6d1c27707c29d1985ec62ff63be0e6427c3",
    "receiptId": "947f7d3339f549221116b1fa6ee11729b2dc7bb2c4de854a0365db9326d7ca64",
    "recipeHash": "8001f1e3c93a92730720011af0f391ac27ed58aedeb0cbb24030983b3698e311",
    "checkerSourceHash": "9fc12f8d3e7fc5f353f40dc8cc3b30a46fb778a02c5e25fdd693bb070bbf0c09",
    "transcriptHash": "ddfe908380cd1f0eb9809099bea1426befaaaea2038a760deb0212d184820d6b",
    "outputsHash": "ac4d80cdb9cdd687d1dae47248762096cfc26842fe9d4d4032a98c9cbb03157f",
    "outcome": "passed",
    "cases": 121,
    "totalCases": 121
  }
]
```

All three receipts declare `authority: bounded-check-only` and environment
`ecmascript-bigint`, a 256-bit bound and a 2,048-case limit. The checker source
hash was independently recomputed from the exact source bytes read at GitHub
head `54478d2d3123956362f3ce672a61f3a74eee9592`; it matches every live
receipt. The private backup reports functional-core source hash
`1f548ab94b675ad72aa3e16fd7bd94fbe2b6c125ec69b0d227066d84cdae47e0`,
matching that head's `hosted/lib/kernel-pin.ts`. This checks the reported
source bindings, not a signed deployment or identity attestation.

The corrected recipe shares the initial recipe/output/transcript fingerprints,
but has a distinct claim-revision hash and receipt ID. It earned no extra
contribution record. The three checks consumed 243 cases: 121 + 1 + 121.

The full private transcript, backup, independent verifier and source bytes were
preserved in `Research-Kernel-MCP-acceptance-2026-10-03.zip`.
Archive SHA-256: `27c52f75cf3b0e112a0937661fdb425a6137f018757dddba1d46c78a75062b41`.
Transcript SHA-256: `a8778e7630029d09b1865e957557051558edb68241851a51e0b5c0cf68cc1c9d`.
The archive includes account-bound backup data and remains private; only
synthetic results and non-identifying receipt bindings appear here.

## Remaining integration limits

The earlier missing data-tool bindings are resolved for this runner. The two
remaining surfaces have not passed acceptance:

- **Connected ChatGPT panel:** `rk_open_memory` returned the workspace, but the
  available computer-use inventory exposed no mounted MCP App/sidebar or
  conversation-panel tab. A successful data result does not demonstrate that
  selecting the claim displays its scope/receipts or that a panel check refreshes
  the workspace. The required resource is `ui://rk/memory.html`, served by
  MCP `resources/read` and connected to the host's `tools/call` bridge.
- **Real authenticated browser/WebMCP:** the live Site opened to **Log in to
  access**. Real WebMCP discovery on that signed-out document returned **No
  WebMCP tools are available in this document.** Following its visible
  **Continue with ChatGPT** link reached OpenAI's sign-in screen. A secure
  sign-in request returned `submitted` with Google selected, but the next visible
  page was **Session ended**, reporting **invalid_state** and an expired sign-in
  session. The authenticated Site application was not reached. This is no
  evidence about its registrations, and no browser-side research tool was executed.

The Site inspection confirmed published version 3 and an owner-only custom
audience: one allowed account, no editors/groups/external visitors, unchanged
access-policy revision 1. No deployment, audience change, invitation,
`rk_package_publish`, billing charge or transferable-token action was
performed in this run. The private journal contains exactly six commands:
`addClaim`, `checkClaim`, `reviseClaim`, `checkClaim`, `reviseClaim`,
`checkClaim`.

To finish the integration boundary, inspect this saved synthetic workspace in
the actual connected ChatGPT panel, select **Square of a sum**, verify the
declared scope and receipt results, run a bounded check and verify its updated
workspace revision. Separately, complete normal sign-in to the private Site and
execute its actually registered WebMCP tools. Record real observations and
receipts before marking either check passed. Registry-contract tests and a
standalone or simulated widget do not establish those results.

This acceptance covers only the finite synthetic recipes. It does not establish
the prose statement outside the grid, a theorem, independent experimental/formal
verification, federation, billing or financial-token functionality.
