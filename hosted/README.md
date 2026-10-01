# Research Kernel shared memory pilot

Private, Site-hosted scientific memory, implemented using functional core / imperative shell (FCIS). The TypeScript hosted service is an additive companion to the existing Python MCP kernel. It does not execute the Python process inside a Worker.

## Working product

- Isolated research workspaces with owner, editor and reader roles. Invitations bind to a verified ChatGPT email; accepted membership binds to the Site-scoped account ID.
- Immutable claim revisions with explicit category, statement, assumptions, scope and dependency fingerprints.
- A bounded integer interpreter: exact BigInt arithmetic, 1–3 finite variables, up to 2,048 combinations, signed remainder, exponents in 0–8 and a 256-bit output bound. It has no arbitrary code execution, subprocess or network capability.
- Checker receipts bind the revision, recipe, checker source, arithmetic environment, aggregate input/output transcript and outcome. Counterexamples and inconclusive results are retained. A pass concerns the recipe and its finite grid, not a theorem or the prose claim.
- Transitive review flags after dependency revision, checker failure or a current-revision negative evidence assertion. An unverified objection requests review without changing its source claim’s checker verdict. Old receipts remain tied to their original revisions.
- Owner-selected CC BY 4.0 packages with canonical digests. Catalog access follows the Site audience. Exporting a package makes an intentionally shareable file; withdrawing cannot recall previously exported copies.
- Failure memory searches every claim revision, scope and negative evidence summary. Corrected claims retain earlier counterexamples with the original recipe, assumptions and receipt; old failures do not determine the current revision’s status.
- Imported claims start unverified; external receipts never become local checker authority.
- A non-transferable, non-monetary contribution ledger. The first pass or counterexample for a recipe/checker/outcome gets one point per workspace. Identical replays receive no additional points. Usage counts prepare a hosted service for future billing; this pilot charges nothing.
- Owner-only private snapshot/journal exports and exact pinned-core replay checks. Exported backups include identities and must remain private.
- 17 stateless Streamable HTTP MCP tools at POST /mcp, plus a MCP App resource with sidebar and conversation-panel entrypoints. Browser WebMCP adapters use the same operations.

## FCIS boundary

`lib/core/` has no filesystem, network, clock, randomness, storage, authentication transport or model calls. An authenticated actor, timestamp, candidate ID and deterministic SHA-256 provider are captured by the shell and supplied to `transition`. Strict closed commands produce reject or an accepted immutable snapshot with an expected revision and an empty external-effect plan.

`lib/store.ts` is the D1 shell. A transactional batch commits the version-checked snapshot, exact command/context, result, journal hash and selected catalog projection together. A conditional insert admits only the winning candidate. Request IDs are actor/workspace bound and idempotent; reuse with different input fails. Failed writes roll back receipts, points, usage and projections. Response failures after commit recover the existing candidate.

This follows FCIS and selected ZenoFCIS patterns. It is not a direct Rust ZenoFCIS mount and does not claim an M6 composition theorem, mechanized refinement, cryptographic identity attestation or a signed scientific certificate. D1 and Sites' trusted identity boundary remain infrastructure assumptions.

`scripts/pin-checker.mjs` hashes the exact checker bytes and the full functional-core source. `verifyReplay` reconstructs each transition, checks gap-free revisions, prior/current roots, context lineage and exact results. It rejects altered history and source-version drift. This establishes journal consistency under the recorded identity context, not independent authentication of exported actors. Replay of an older source version requires that source version.

## Run and validate

Use Node 24 for tests, including the real SQLite-backed D1 adapter. Install from `pnpm-lock.yaml` using the Sites dependency helper or pnpm.

```sh
pnpm test
pnpm typecheck
pnpm build
pnpm db:generate
```

The tests cover bounded arithmetic, strict admission, role isolation, dependency invalidation, package tampering, neutral/deduplicated contributions, exact replay, SQL migrations, reopened persistence, injected transaction failures, concurrent commits, idempotent retries and MCP authorization.

The local D1 migrations must be applied in order to the preview database. Publishing applies the same migrations to production. No research data is seeded by migrations.

The deployment is private. A teammate needs both Site access and workspace membership. Discovery carries no research data. Data tools require a real user identity; a service credential alone cannot read private user records. The Site-provisioned plugin must be installed/connected by the account before ChatGPT can call it.

Limits are explicit pilot quotas: 20 workspaces per owner; 30 members/invitations, 200 claims, 20 revisions per claim, 400 evidence items, 500 receipts, 100 packages, 3,000 changes, an 850 KB snapshot and a 4 MB command/context/result journal per workspace. The catalog returns its 20 newest selected packages.

## Commercial next steps

The sellable unit is hosted private collaboration and reproducible work: storage, team access, review history and metered verification jobs. Before charging, add a payment-provider integration, enforce server-side entitlements and budgets, measure operating costs, and validate demand with pilot teams.

A transferable token, token sale, financial rewards, independent verifier registry, arbitrary experimental replay, Lean proof checking and networked federation are not launched here. Selected-package exchange and local checking are implemented first. Contribution points are descriptive activity records, not financial assets, Sybil-resistant reputation or a truth score.

## Python interoperability

The Python server adds `rk_export_scoped_claim` for one explicitly selected claim/ hypothesis/result and `rk_import_evidence_package` for a digest-checked package. Exports omit local status, scores, hidden metadata, run content and dependency content. Imports use CANDIDATE with triage-only authority; the existing promotion gate cannot mistake them for scientific support.

The two servers retain their own storage and tools. ChatGPT can use the export command's claim input with the hosted `rk_claim_add`, then send a selected package back to the Python importer.

## Validation limitation

Protocol, database and registry-contract tests run locally. The browser preview was checked for layout, navigation and the signed-out state; the workbench layout was repaired so notifications no longer displace its columns. The available preview has no authenticated account or WebMCP registrations, so authenticated browser actions, real-host WebMCP behavior and connected ChatGPT sidebar actions remain unverified. Installation alone does not establish a successful data-tool call.

Run `rk_workspaces_list` after connecting the Site plugin. Then create a private workspace, record the built-in bounded example and run `rk_check`: the exact grid should return 121/121 cases passed. Revise the recipe to omit the cross term and check it again; the saved counterexample must remain discoverable after a corrected revision is added. These are synthetic acceptance examples, not scientific results.

The functional-core source pin changes when transition semantics or helpers change. Existing backups remain readable; exact replay requires the matching source version for every recorded commit. The deployment was inspected before this update and contained no research workspaces.
