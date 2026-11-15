import { claimStatus, current, type Claim, type Workspace } from "./model";

/**
 * Negative information is not a global no-good by default.
 * Hard: a locally replayable bounded checker counterexample for ONE exact recipe/revision.
 * Soft: an explanatory observation or conjectured obstruction, including asserted proofs.
 * Neither class implies an impossibility result for an unverified family of candidates.
 */
export type NegativeInsight = {
  id: string;
  classification: "hard" | "soft";
  authority: "bounded-check-only" | "unverified";
  claimId: string;
  originalRevision: string;
  currentRevision: string;
  currentStatus: ReturnType<typeof claimStatus>;
  originalScope: string;
  checkedScope: string | null;
  assumptions: string;
  attempt: string;
  failureReason: string;
  checkedWitness: { inputs: Record<string, number>; left: string; right: string } | null;
  reportedWitness: string | null;
  source: { receiptId: string | null; evidenceId: string | null; sourceUri: string; transcriptHash: string | null };
  exclusion: {
    safeToPrune: boolean;
    appliesOnlyTo: string;
    generalizedPruningAuthorized: false;
  };
  candidateGeneralization: string | null;
  alternativeRepresentation: string | null;
  revisitWhen: string[];
  information: {
    rank: number;
    present: string[];
    missing: string[];
    nextBestAction: string;
    // This rank measures documented/replayable information, never scientific truth.
    rankingAuthority: "discovery-triage-only";
  };
};

const filled = (s: string | null | undefined) => Boolean(s?.trim());
function annotate(i: Omit<NegativeInsight, "information">): NegativeInsight {
  // Retain every failure even if it lacks details; expose what would strengthen it.
  const fields: Record<string, boolean> = {
    attempt: filled(i.attempt),
    failureReason: filled(i.failureReason),
    applicability: filled(i.originalScope),
    assumptions: filled(i.assumptions),
    witness: i.checkedWitness !== null || filled(i.reportedWitness),
    representationAlternative: filled(i.alternativeRepresentation),
    revisitConditions: i.revisitWhen.length > 0,
    generalizationHypothesis: filled(i.candidateGeneralization),
  };
  const present = Object.keys(fields).filter(k => fields[k]);
  const missing = Object.keys(fields).filter(k => !fields[k]);
  // Verified witness is a stronger immediate pruning instrument than prose; do
  // not mistake this deterministic triage rank for proof of wider applicability.
  const rank = (i.classification === "hard" ? 100 : 0) + present.length * 10
    + (i.revisitWhen.length ? 2 : 0) + (filled(i.alternativeRepresentation) ? 2 : 0);
  const nextBestAction = i.classification === "hard"
    ? "Minimize the checked witness, explain the root cause, and separately prove any proposed generalization before excluding a larger candidate class."
    : i.reportedWitness
      ? "Reproduce the reported witness in a version-pinned checker; keep all proposed generalizations advisory until independently proved."
      : "Find a reproducible witness or an independently checked impossibility certificate; preserve the idea for changed representations.";
  return { ...i, information: { rank, present, missing, nextBestAction, rankingAuthority: "discovery-triage-only" } };
}

export function negativeInsights(state: Workspace): NegativeInsight[] {
  const out: NegativeInsight[] = [];
  const claimById = new Map(state.claims.map(c => [c.id, c]));
  const revision = (claim: Claim, digest: string) => claim.revisions.find(r => r.hash === digest);
  for (const receipt of state.receipts) {
    if (receipt.result.outcome !== "counterexample" || !receipt.result.counterexample) continue;
    const claim = claimById.get(receipt.claimId);
    if (!claim) continue;
    const original = revision(claim, receipt.claimRevision);
    if (!original || !original.recipe) continue;
    out.push(annotate({
      id: "receipt:" + receipt.id,
      classification: "hard", authority: "bounded-check-only",
      claimId: claim.id, originalRevision: original.hash, currentRevision: current(claim).hash,
      currentStatus: claimStatus(state, claim), originalScope: original.scope,
      checkedScope: receipt.result.scope, assumptions: original.assumptions,
      attempt: original.recipe.left + " == " + original.recipe.right,
      failureReason: "Exact integer-grid evaluation found unequal outputs for the displayed input.",
      checkedWitness: receipt.result.counterexample, reportedWitness: null,
      source: { receiptId: receipt.id, evidenceId: null, sourceUri: "", transcriptHash: receipt.transcriptHash },
      exclusion: {
        safeToPrune: true,
        appliesOnlyTo: "The exact recipe of claim revision " + original.hash + " under its declared finite grid, assuming this pinned checker is trusted.",
        generalizedPruningAuthorized: false,
      },
      candidateGeneralization: null, alternativeRepresentation: null, revisitWhen: [],
    }));
  }
  for (const evidence of state.evidence) {
    if (evidence.kind !== "negative") continue;
    const claim = claimById.get(evidence.claimId);
    if (!claim) continue;
    const original = revision(claim, evidence.revisionHash);
    if (!original) continue;
    const n = evidence.negative;
    out.push(annotate({
      id: "evidence:" + evidence.id, classification: "soft", authority: "unverified",
      claimId: claim.id, originalRevision: original.hash, currentRevision: current(claim).hash,
      currentStatus: claimStatus(state, claim), originalScope: n?.scope || original.scope,
      checkedScope: null, assumptions: n?.assumptions || original.assumptions,
      attempt: n?.attempt || original.statement, failureReason: n?.failureReason || evidence.summary,
      checkedWitness: null, reportedWitness: n?.observedCounterexample || null,
      source: { receiptId: null, evidenceId: evidence.id, sourceUri: evidence.uri, transcriptHash: null },
      exclusion: {
        safeToPrune: false,
        appliesOnlyTo: "Unverified analysis of claim revision " + original.hash + "; not a sound pruning rule.",
        generalizedPruningAuthorized: false,
      },
      candidateGeneralization: n?.candidateGeneralization || null,
      alternativeRepresentation: n?.alternativeRepresentation || null,
      revisitWhen: n?.revisitWhen || [],
    }));
  }
  return out.sort((a, b) => b.information.rank - a.information.rank || a.id.localeCompare(b.id));
}

/** Search full historical context and recorded objections, not only current claims. */
export function queryNegativeInsights(state: Workspace, query: string, classification: "all" | "hard" | "soft" = "all"): NegativeInsight[] {
  const q = query.trim().toLowerCase();
  const claims = new Map(state.claims.map(c => [c.id, c]));
  return negativeInsights(state).filter(i => {
    if (classification !== "all" && i.classification !== classification) return false;
    if (!q) return true;
    const claim = claims.get(i.claimId);
    return [
      i.attempt, i.failureReason, i.originalScope, i.checkedScope ?? "",
      i.assumptions, i.reportedWitness ?? "", i.candidateGeneralization ?? "",
      i.alternativeRepresentation ?? "", ...i.revisitWhen,
      ...(claim ? claim.revisions.flatMap(r => [r.title, r.statement, r.scope, r.assumptions]) : []),
    ].join(" ").toLowerCase().includes(q);
  });
}
