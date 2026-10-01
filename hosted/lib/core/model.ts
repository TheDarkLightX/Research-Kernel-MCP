import type { Recipe, CheckResult } from "./checker";
export type Hash = (canonical: string) => string;
export type Role = "owner" | "editor" | "reader";
export type Actor = { userId: string; email: string; name: string };
export type ClaimKind = "hypothesis" | "literature" | "experiment" | "formal" | "bounded";
export type ClaimInput = {
  title: string; statement: string; kind: ClaimKind; assumptions: string;
  scope: string; recipe: Recipe | null; dependencies: string[];
};
export type ClaimRevision = ClaimInput & {
  number: number; hash: string; author: string; createdAt: string;
  dependencyHashes: Record<string, string>;
};
export type Claim = { id: string; revisions: ClaimRevision[]; needsReview: boolean; importedFrom: string | null };
export type Evidence = { id: string; claimId: string; revisionHash: string; kind: "source" | "experiment" | "formal" | "negative"; uri: string; summary: string; artifactHash: string | null; author: string; createdAt: string; authority: "unverified" };
export type Receipt = {
  id: string; claimId: string; claimRevision: string; recipeHash: string;
  checker: string; checkerSourceHash: string; transcriptHash: string;
  result: CheckResult; requestedBy: string; createdAt: string;
  authority: "bounded-check-only";
  environment: { arithmetic: "ecmascript-bigint"; bitLimit: 256; caseLimit: 2048 };
};
export type Publication = { id: string; hash: string; claimId: string; title: string; claim: ClaimRevision; receipts: Receipt[]; evidence: Evidence[]; createdAt: string; license: "CC-BY-4.0"; authority: "evidence-package"; revoked: boolean };
export type LedgerEntry = { id: string; actor: string; claimId: string; revisionHash: string; reason: "reproducible-check" | "counterexample"; points: number; createdAt: string; transferable: false };
export type Workspace = {
  schema: "rk-memory/1"; id: string; name: string; revision: number;
  members: (Actor & { role: Role })[];
  invitations: { email: string; role: "editor" | "reader" }[];
  claims: Claim[]; evidence: Evidence[]; receipts: Receipt[];
  publications: Publication[]; ledger: LedgerEntry[];
  usage: { checks: number; cases: number; exports: number; journalBytes: number };
  audit: { id: string; actor: string; kind: string; at: string; revision: number }[];
};
export type Context = { actor: Actor; now: string; id: string; checkerSourceHash: string };
export type Command =
  | { type: "addClaim"; claim: ClaimInput }
  | { type: "reviseClaim"; claimId: string; expectedHash: string; claim: ClaimInput }
  | { type: "attachEvidence"; claimId: string; expectedHash: string; kind: Evidence["kind"]; uri: string; summary: string; artifactHash: string | null }
  | { type: "checkClaim"; claimId: string; expectedHash: string }
  | { type: "publishClaim"; claimId: string; expectedHash: string }
  | { type: "revokePublication"; publicationId: string }
  | { type: "importPackage"; packet: Publication }
  | { type: "invite"; email: string; role: "editor" | "reader" }
  | { type: "removeMember"; userId: string }
  | { type: "removeInvitation"; email: string }
  | { type: "join" };
export type Decision = { decision: "reject"; code: string; message: string } | {
  decision: "accept"; expectedRevision: number; state: Workspace;
  result: Record<string, unknown>; effects: readonly [];
};
export const current = (c: Claim): ClaimRevision => c.revisions[c.revisions.length - 1];
export function hasNegativeEvidence(state: Workspace, claim: Claim): boolean {
  return state.evidence.some(e => e.claimId === claim.id && e.revisionHash === current(claim).hash && e.kind === "negative");
}
// Failure memory spans every revision. A corrected claim must not erase its lesson.
export function hasFailureHistory(state: Workspace, claim: Claim): boolean {
  return state.receipts.some(r => r.claimId === claim.id && r.result.outcome === "counterexample")
    || state.evidence.some(e => e.claimId === claim.id && e.kind === "negative");
}
export function matchesClaimQuery(state: Workspace, claim: Claim, query: string, history = false): boolean {
  const revisions = history ? claim.revisions : [current(claim)];
  const text = revisions.map(r => [r.title, r.statement, r.assumptions, r.scope].join(" "));
  if (history) text.push(...state.evidence.filter(e => e.claimId === claim.id && e.kind === "negative").map(e => e.summary));
  return text.join(" ").toLowerCase().includes(query.trim().toLowerCase());
}
export function canonical(value: unknown): string {
  if (value === null || typeof value !== "object") {
    const v = JSON.stringify(value);
    if (v === undefined) throw new Error("Only closed JSON values can be encoded.");
    return v;
  }
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  return "{" + Object.keys(value).sort().map(k => JSON.stringify(k) + ":" + canonical((value as Record<string, unknown>)[k])).join(",") + "}";
}
export function roleFor(state: Workspace, actor: Actor): Role | null {
  return state.members.find(m => m.userId === actor.userId)?.role ?? null;
}
export function createWorkspace(id: string, name: string, actor: Actor): Workspace {
  return { schema: "rk-memory/1", id, name, revision: 0, members: [{ ...actor, role: "owner" }], invitations: [], claims: [], evidence: [], receipts: [], publications: [], ledger: [], usage: { checks: 0, cases: 0, exports: 0, journalBytes: 0 }, audit: [] };
}
export function claimStatus(state: Workspace, claim: Claim): "needs-review" | "counterexample" | "bounded-checked" | "unverified" {
  if (claim.needsReview) return "needs-review";
  const rs = state.receipts.filter(r => r.claimId === claim.id && r.claimRevision === current(claim).hash);
  if (rs.some(r => r.result.outcome === "counterexample")) return "counterexample";
  if (rs.some(r => r.result.outcome === "passed")) return "bounded-checked";
  return "unverified";
}
