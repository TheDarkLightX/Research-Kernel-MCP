# Hosted scientific memory

The `hosted/` directory contains a private Sites-compatible research memory companion. It adds revision-bound claims, finite-domain checking, shared workspaces, selected evidence packages, negative result memory and a non-monetary contribution ledger using FCIS.

See [the hosted README](../hosted/README.md) for the architecture, exact authority limits, quotas, tests and setup. The existing Python server remains available with its original research tools and promotion gates.

Python tools added:

- `rk_export_scoped_claim`: select one claim, hypothesis or result, supply its title, assumptions and scope, and prepare an unverified hosted claim command. No status, confidence, hidden metadata or private run content is exported.
- `rk_import_evidence_package`: validate a selected hosted package's canonical fingerprints and import it as CANDIDATE / triage-only. External receipts cannot satisfy the local scientific-authority gate.

The fixture in `tests/shared-package.json` was produced by the TypeScript functional core to check canonical interoperability. It is synthetic arithmetic test data, not a research finding or a preloaded production record.

Hosted UI and MCP operations share the same validated transition and atomic D1 commit path. It follows FCIS and relevant ZenoFCIS patterns; the Rust ZenoFCIS library is not directly mounted, and no formal composition/refinement guarantee is claimed.

No billing, transferable token or token sale is active. Usage and non-transferable contribution records provide a pilot foundation. Paid workspaces and independently verified jobs require a subsequent billing and verifier integration.

The Python package is constrained to MCP SDK 1.x, which provides the FastMCP API used by this server. A discovery regression test fails if that server API is unavailable; SDK 2.x needs an explicit migration rather than a silent fallback to a non-running server.
