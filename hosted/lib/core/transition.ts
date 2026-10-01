import { checkRecipe, CHECKER_ID } from "./checker";
import { canonical, current, roleFor, claimStatus, type Workspace, type Command, type Context, type Decision, type Hash, type ClaimInput, type ClaimRevision, type Publication } from "./model";
import { commandSchema } from "./validation";

export function publicationDigest(packet: Omit<Publication, "hash"> | Publication, hash: Hash): string {
  const { hash: ignored, revoked: ignoredRevocation, ...content } = packet as Publication;
  return hash(canonical({ schema: "rk-evidence-package/1", ...content }));
}
export function revisionDigest(value: ClaimRevision | Omit<ClaimRevision, "hash">, hash: Hash) {
  const { author: _a, createdAt: _t, hash: _h, ...contract } = value as ClaimRevision;
  return hash(canonical(contract));
}
function dependencyIssue(r: ClaimRevision, state: Workspace): boolean {
  return r.dependencies.some(id => {
    const c = state.claims.find(c => c.id === id);
    return !c || current(c).hash !== r.dependencyHashes[id] || ["counterexample", "needs-review"].includes(claimStatus(state, c));
  });
}
function revision(input: ClaimInput, state: Workspace, ctx: Context, hash: Hash, number: number): ClaimRevision {
  const dependencyHashes = Object.fromEntries(input.dependencies.slice().sort().map(id => {
    const dep = state.claims.find(c => c.id === id);
    if (!dep) throw new Error("Every dependency must exist in this workspace.");
    return [id, current(dep).hash];
  }));
  const value = { ...input, dependencies: [...new Set(input.dependencies)].sort(), dependencyHashes, number, author: ctx.actor.userId, createdAt: ctx.now };
  return { ...value, hash: revisionDigest(value, hash) };
}
export function transition(before: Workspace, raw: unknown, ctx: Context, hash: Hash): Decision {
  const reject = (code: string, message: string): Decision => ({ decision: "reject", code, message });
  const role = roleFor(before, ctx.actor);
  const parsed = commandSchema.safeParse(raw);
  if (!parsed.success) return reject("invalid-command", parsed.error.issues.map(i => i.path.join(".") + ": " + i.message).slice(0, 3).join("; "));
  const cmd = parsed.data as Command;
  if (cmd.type !== "join" && !role) return reject("forbidden", "Workspace membership is required.");
  if (cmd.type !== "join" && role === "reader") return reject("forbidden", "Readers cannot change research records.");
  if (["invite", "removeMember", "removeInvitation", "publishClaim", "revokePublication"].includes(cmd.type) && role !== "owner") return reject("forbidden", "Only the workspace owner can manage access or publication.");
  if (before.audit.length >= 3000) return reject("capacity", "This pilot workspace reached its 3,000-change limit. Export its records before starting another workspace.");
  const state: Workspace = structuredClone(before);
  let result: Record<string, unknown> = {};
  try {
    if (cmd.type === "join") {
      if (role) return reject("already-member", "You already belong to this workspace.");
      const invitation = state.invitations.find(i => i.email === ctx.actor.email.toLowerCase());
      if (!invitation) return reject("forbidden", "No invitation matches this authenticated email.");
      state.members.push({ ...ctx.actor, role: invitation.role });
      state.invitations = state.invitations.filter(i => i !== invitation);
      result = { workspaceId: state.id };
    } else if (cmd.type === "invite") {
      const email = cmd.email.toLowerCase();
      if (state.members.some(m => m.email.toLowerCase() === email)) return reject("already-member", "This account is already a member.");
      if (state.members.length + state.invitations.length >= 30) return reject("capacity", "At most 30 accounts per pilot workspace.");
      state.invitations = state.invitations.filter(i => i.email !== email);
      state.invitations.push({ email, role: cmd.role });
      result = { email, role: cmd.role, delivery: "No email was sent. The account also needs access to the Site." };
    } else if (cmd.type === "removeInvitation") {
      state.invitations = state.invitations.filter(i => i.email !== cmd.email.toLowerCase());
    } else if (cmd.type === "removeMember") {
      if (state.members.find(m => m.userId === cmd.userId)?.role === "owner") return reject("owner-required", "The owner cannot be removed.");
      state.members = state.members.filter(m => m.userId !== cmd.userId);
    } else if (cmd.type === "addClaim") {
      if (state.claims.length >= 200) return reject("capacity", "At most 200 claims per pilot workspace.");
      const r = revision(cmd.claim, state, ctx, hash, 1);
      state.claims.push({ id: ctx.id, revisions: [r], needsReview: dependencyIssue(r, state), importedFrom: null });
      result = { claimId: ctx.id, revisionHash: r.hash };
    } else if (cmd.type === "revokePublication") {
      const p = state.publications.find(p => p.id === cmd.publicationId);
      if (!p) return reject("not-found", "Publication does not exist.");
      p.revoked = true;
      result = { publicationId: p.id, revoked: true };
    } else if (cmd.type === "importPackage") {
      if (cmd.packet.revoked || publicationDigest(cmd.packet, hash) !== cmd.packet.hash || revisionDigest(cmd.packet.claim, hash) !== cmd.packet.claim.hash) return reject("invalid-package", "The package is revoked or its canonical digests do not match.");
      if (cmd.packet.receipts.some(r => r.claimId !== cmd.packet.claimId || r.claimRevision !== cmd.packet.claim.hash || r.transcriptHash !== hash(canonical(r.result)) || !cmd.packet.claim.recipe || r.recipeHash !== hash(canonical(cmd.packet.claim.recipe))) || cmd.packet.evidence.some(e => e.claimId !== cmd.packet.claimId || e.revisionHash !== cmd.packet.claim.hash)) return reject("invalid-package", "Evidence or receipt fingerprints do not match the selected claim.");
      if (state.claims.length >= 200) return reject("capacity", "At most 200 claims per pilot workspace.");
      if (state.claims.some(c => c.importedFrom === cmd.packet.hash)) return reject("duplicate-package", "This package was already imported.");
      const { title, statement, kind, assumptions, scope, recipe } = cmd.packet.claim;
      const checked = commandSchema.safeParse({ type: "addClaim", claim: { title, statement, kind, assumptions, scope, recipe, dependencies: [] } });
      if (!checked.success) return reject("invalid-package", "Imported claim is invalid.");
      const r = revision({ title, statement, kind, assumptions, scope, recipe, dependencies: [] }, state, ctx, hash, 1);
      state.claims.push({ id: ctx.id, revisions: [r], needsReview: Object.keys(cmd.packet.claim.dependencyHashes).length > 0, importedFrom: cmd.packet.hash });
      if (state.evidence.length >= 400) return reject("capacity", "Evidence limit reached.");
      state.evidence.push({ id: ctx.id + "-source", claimId: ctx.id, revisionHash: r.hash, kind: "source", uri: "rk-package:" + cmd.packet.hash, summary: "Imported evidence package. External receipts are untrusted; run a local check. " + cmd.packet.evidence.map(e => e.summary).join("\n").slice(0, 3000), artifactHash: cmd.packet.hash, author: ctx.actor.userId, createdAt: ctx.now, authority: "unverified" });
      result = { claimId: ctx.id, authority: "unverified", externalDependencies: Object.keys(cmd.packet.claim.dependencyHashes) };
    } else {
      const claim = state.claims.find(c => c.id === cmd.claimId);
      if (!claim) return reject("not-found", "Claim does not exist in this workspace.");
      const r = current(claim);
      if (r.hash !== cmd.expectedHash) return reject("stale-revision", "The claim changed. Reload and review the latest revision.");
      if (cmd.type === "reviseClaim") {
        if (claim.revisions.length >= 20) return reject("capacity", "At most 20 revisions per pilot claim.");
        if (cmd.claim.dependencies.includes(claim.id)) return reject("dependency-cycle", "A claim cannot depend on itself.");
        const dependsOn = (id: string, seen = new Set<string>()): boolean => {
          if (id === claim.id) return true; if (seen.has(id)) return false; seen.add(id);
          return (state.claims.find(c => c.id === id) ? current(state.claims.find(c => c.id === id)!).dependencies : []).some(d => dependsOn(d, seen));
        };
        if (cmd.claim.dependencies.some(d => dependsOn(d))) return reject("dependency-cycle", "Dependencies must form an acyclic graph.");
        const next = revision(cmd.claim, state, ctx, hash, r.number + 1);
        claim.revisions.push(next); claim.needsReview = dependencyIssue(next, state);
        const affected = new Set([claim.id]);
        let changed = true;
        while (changed) {
          changed = false;
          for (const c of state.claims) if (!affected.has(c.id) && current(c).dependencies.some(d => affected.has(d))) { c.needsReview = true; affected.add(c.id); changed = true; }
        }
        result = { claimId: claim.id, revisionHash: next.hash, affectedClaims: [...affected].filter(id => id !== claim.id) };
      } else if (cmd.type === "attachEvidence") {
        if (state.evidence.length >= 400) return reject("capacity", "At most 400 evidence entries per workspace.");
        if (cmd.uri && !/^(https?:\/\/|doi:|rk-package:)/i.test(cmd.uri)) return reject("invalid-uri", "Use an http(s) URL, doi: or rk-package: reference.");
        state.evidence.push({ id: ctx.id, claimId: claim.id, revisionHash: r.hash, kind: cmd.kind, uri: cmd.uri, summary: cmd.summary, artifactHash: cmd.artifactHash, author: ctx.actor.userId, createdAt: ctx.now, authority: "unverified" });
        result = { evidenceId: ctx.id, authority: "unverified" };
      } else if (cmd.type === "checkClaim") {
        if (!r.recipe || r.kind !== "bounded") return reject("unsupported-check", "This pilot checks bounded integer recipes. Other evidence remains unverified.");
        if (state.receipts.length >= 500) return reject("capacity", "At most 500 verification receipts per workspace.");
        if (claim.needsReview || dependencyIssue(r, state)) return reject("dependency-review", "Revise this claim after reviewing its changed or failed dependencies.");
        const check = checkRecipe(r.recipe, hash), recipeHash = hash(canonical(r.recipe));
        const receipt = { id: ctx.id, claimId: claim.id, claimRevision: r.hash, recipeHash, checker: CHECKER_ID, checkerSourceHash: ctx.checkerSourceHash, transcriptHash: hash(canonical(check)), result: check, requestedBy: ctx.actor.userId, createdAt: ctx.now, authority: "bounded-check-only" as const, environment: { arithmetic: "ecmascript-bigint" as const, bitLimit: 256 as const, caseLimit: 2048 as const } };
        const previous = state.receipts.some(v => v.recipeHash === recipeHash && v.checkerSourceHash === ctx.checkerSourceHash && v.result.outcome === check.outcome);
        state.receipts.push(receipt);
        state.usage.checks++; state.usage.cases += check.cases;
        if (!previous && check.outcome !== "inconclusive") state.ledger.push({ id: ctx.id, actor: ctx.actor.userId, claimId: claim.id, revisionHash: r.hash, reason: check.outcome === "passed" ? "reproducible-check" : "counterexample", points: 1, createdAt: ctx.now, transferable: false });
        // Failed dependencies propagate review, while immutable prior receipts remain inspectable.
        if (check.outcome === "counterexample") {
          const affected = new Set([claim.id]); let changed = true;
          while (changed) { changed = false; for (const c of state.claims) if (!affected.has(c.id) && current(c).dependencies.some(d => affected.has(d))) { c.needsReview = true; affected.add(c.id); changed = true; } }
        }
        result = { receipt, contributionRecorded: !previous && check.outcome !== "inconclusive" };
      } else if (cmd.type === "publishClaim") {
        if (claim.needsReview || dependencyIssue(r, state)) return reject("dependency-review", "Review stale or failed dependencies before publication.");
        if (state.publications.length >= 100) return reject("capacity", "At most 100 publication packages per workspace.");
        if (state.publications.some(p => p.claim.hash === r.hash && !p.revoked)) return reject("already-published", "This revision already has a publication package.");
        const packet: Publication = {
          id: ctx.id, claimId: claim.id, title: r.title, hash: "", claim: { ...r, author: "contributor" },
          receipts: state.receipts.filter(v => v.claimId === claim.id && v.claimRevision === r.hash).map(v => ({ ...v, requestedBy: "contributor" })),
          evidence: state.evidence.filter(e => e.claimId === claim.id && e.revisionHash === r.hash).map(e => ({ ...e, author: "contributor" })),
          createdAt: ctx.now, license: "CC-BY-4.0", authority: "evidence-package", revoked: false,
        };
        packet.hash = publicationDigest(packet, hash);
        if (new TextEncoder().encode(canonical(packet)).length > 200000) return reject("capacity", "Selected package exceeds 200 KB. Reduce evidence summaries before publication.");
        state.publications.push(packet); state.usage.exports++;
        result = { publicationId: packet.id, packetHash: packet.hash, audience: "Site access policy applies" };
      }
    }
    state.usage.journalBytes += new TextEncoder().encode(canonical(cmd) + canonical(ctx) + canonical(result)).length;
    if (state.usage.journalBytes > 4000000) return reject("capacity", "The pilot journal reached 4 MB. Export your workspace and start a new one.");
    state.revision++;
    state.audit.push({ id: ctx.id, actor: ctx.actor.userId, kind: cmd.type, at: ctx.now, revision: state.revision });
    if (new TextEncoder().encode(canonical(state)).length > 850000) return reject("capacity", "Workspace storage limit reached. Export records and create another workspace.");
    return { decision: "accept", expectedRevision: before.revision, state, result, effects: [] };
  } catch (e) { return reject("invalid-transition", e instanceof Error ? e.message : "Transition rejected."); }
}
