import { z } from "zod";
const hash = z.string().regex(/^[a-f0-9]{64}$/);
const id = z.string().min(1).max(100);
export const recipeSchema = z.object({
  checker: z.literal("integer-grid/v1"),
  variables: z.record(z.string().regex(/^[a-zA-Z][a-zA-Z0-9_]{0,15}$/), z.object({ min: z.number().int().min(-1000000).max(1000000), max: z.number().int().min(-1000000).max(1000000) }).strict()).refine(v => Object.keys(v).length >= 1 && Object.keys(v).length <= 3),
  left: z.string().min(1).max(400), right: z.string().min(1).max(400),
}).strict();
export const claimSchema = z.object({
  title: z.string().trim().min(3).max(180), statement: z.string().trim().min(3).max(6000),
  kind: z.enum(["hypothesis", "literature", "experiment", "formal", "bounded"]),
  assumptions: z.string().max(2000), scope: z.string().trim().min(3).max(2000),
  recipe: recipeSchema.nullable(), dependencies: z.array(id).max(16),
}).strict().refine(c => c.kind === "bounded" ? c.recipe !== null : c.recipe === null, { message: "Only bounded claims may carry an integer-grid recipe." });
const revisionSchema = z.object({
  ...claimSchema.innerType().shape, number: z.number().int().min(1), hash,
  author: id, createdAt: z.string().max(100), dependencyHashes: z.record(id, hash),
}).strict();
const evidenceSchema = z.object({
  id, claimId: id, revisionHash: hash, kind: z.enum(["source", "experiment", "formal", "negative"]),
  uri: z.string().max(2000), summary: z.string().max(4000), artifactHash: hash.nullable(),
  author: id, createdAt: z.string().max(100), authority: z.literal("unverified"),
}).strict();
const receiptSchema = z.object({
  id, claimId: id, claimRevision: hash, recipeHash: hash, checker: z.string().max(100), checkerSourceHash: hash, transcriptHash: hash,
  result: z.object({
    outcome: z.enum(["passed", "counterexample", "inconclusive"]), cases: z.number().int().min(0).max(2048),
    totalCases: z.number().int().min(0).max(2048), scope: z.string().max(2000),
    counterexample: z.object({ inputs: z.record(z.number().int()), left: z.string().max(300), right: z.string().max(300) }).strict().nullable(),
    error: z.string().max(2000).nullable(), outputsHash: hash,
  }).strict(), requestedBy: id, createdAt: z.string().max(100), authority: z.literal("bounded-check-only"),
  environment: z.object({ arithmetic: z.literal("ecmascript-bigint"), bitLimit: z.literal(256), caseLimit: z.literal(2048) }).strict(),
}).strict();
export const publicationSchema = z.object({
  id, hash, claimId: id, title: z.string().max(180), claim: revisionSchema, receipts: z.array(receiptSchema).max(100),
  evidence: z.array(evidenceSchema).max(100), createdAt: z.string().max(100),
  license: z.literal("CC-BY-4.0"), authority: z.literal("evidence-package"), revoked: z.boolean(),
}).strict();
const target = { claimId: id, expectedHash: hash };
export const commandSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("addClaim"), claim: claimSchema }).strict(),
  z.object({ type: z.literal("reviseClaim"), ...target, claim: claimSchema }).strict(),
  z.object({ type: z.literal("attachEvidence"), ...target, kind: evidenceSchema.shape.kind, uri: z.string().max(2000), summary: z.string().trim().min(3).max(4000), artifactHash: hash.nullable() }).strict(),
  z.object({ type: z.literal("checkClaim"), ...target }).strict(),
  z.object({ type: z.literal("publishClaim"), ...target }).strict(),
  z.object({ type: z.literal("revokePublication"), publicationId: id }).strict(),
  z.object({ type: z.literal("importPackage"), packet: publicationSchema }).strict(),
  z.object({ type: z.literal("invite"), email: z.string().email().max(254), role: z.enum(["editor", "reader"]) }).strict(),
  z.object({ type: z.literal("removeMember"), userId: id }).strict(),
  z.object({ type: z.literal("removeInvitation"), email: z.string().email().max(254) }).strict(),
  z.object({ type: z.literal("join") }).strict(),
]);
