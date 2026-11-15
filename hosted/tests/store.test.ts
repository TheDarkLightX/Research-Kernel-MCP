import test from "node:test";
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { SqliteD1 } from "./sqlite-d1";
import { ResearchStore, AppError } from "../lib/store";
import { current, canonical, type Actor } from "../lib/core/model";
import { verifyReplay } from "../lib/replay";
import { owner, editor, reader, input } from "./fixtures";
async function fixture() {
  const db = new SqliteD1(), s = new ResearchStore(db.port());
  const w = await s.create("Private lab name", randomUUID(), owner);
  const out = await s.execute(w.id, 0, randomUUID(), { type: "addClaim", claim: input }, owner);
  return { db, s, w: out.workspace };
}
test("fresh production migrations apply in order, and data survives reopening", async () => {
  const dir = mkdtempSync(join(tmpdir(), "rk-store-")), path = join(dir, "rk.sqlite");
  let db = new SqliteD1(path), s = new ResearchStore(db.port());
  const w = await s.create("Durable lab", randomUUID(), owner);
  await s.execute(w.id, 0, randomUUID(), { type: "addClaim", claim: input }, owner); db.close();
  db = new SqliteD1(path, false); s = new ResearchStore(db.port()); const recovered = await s.read(w.id, owner);
  assert.equal(recovered.claims.length, 1); assert.equal(recovered.revision, 1);
  const backup: any = await s.backup(w.id, owner); assert.equal(verifyReplay(backup.genesis, backup.commits, backup.workspace).verified, true);
  const broken = structuredClone(backup); broken.commits[0].context = broken.commits[0].context.replace("owner@example.test", "changed@example.test");
  assert.throws(() => verifyReplay(broken.genesis, broken.commits, broken.workspace));
  db.close(); rmSync(dir, { recursive: true });
});
test("receipt, usage, credits and audit journal roll back together at a crash point", async () => {
  const { db, s, w } = await fixture(), before = canonical(w);
  db.failAfterStatement = 0;
  await assert.rejects(s.execute(w.id, w.revision, randomUUID(), { type: "checkClaim", claimId: w.claims[0].id, expectedHash: current(w.claims[0]).hash }, owner));
  assert.equal(canonical(await s.read(w.id, owner)), before);
  assert.equal(db.db.prepare("SELECT count(*) AS n FROM workspace_commits").get()!.n, 1); db.close();
});
test("concurrent CAS writers admit exactly one complete candidate", async () => {
  const { db, s, w } = await fixture();
  const cmd = { type: "checkClaim", claimId: w.claims[0].id, expectedHash: current(w.claims[0]).hash };
  const attempts = await Promise.allSettled([s.execute(w.id, w.revision, randomUUID(), cmd, owner), s.execute(w.id, w.revision, randomUUID(), cmd, owner)]);
  assert.equal(attempts.filter(r => r.status === "fulfilled").length, 1);
  const after = await s.read(w.id, owner); assert.equal(after.receipts.length, 1); assert.equal(after.ledger.length, 1); assert.equal(after.audit.length, 2);
  const backup: any = await s.backup(w.id, owner); assert.equal(verifyReplay(backup.genesis, backup.commits, after).revisions, 2); db.close();
});
test("retry reuses the same candidate and rejects reuse with different input", async () => {
  const { db, s, w } = await fixture(), key = randomUUID(), cmd = { type: "checkClaim", claimId: w.claims[0].id, expectedHash: current(w.claims[0]).hash };
  const a = await s.execute(w.id, w.revision, key, cmd, owner), b = await s.execute(w.id, w.revision, key, cmd, owner);
  assert.equal(b.replayed, true); assert.equal(a.result.receipt.id, b.result.receipt.id); assert.equal(b.workspace.receipts.length, 1);
  await assert.rejects(s.execute(w.id, w.revision, key, { type: "publishClaim", claimId: cmd.claimId, expectedHash: cmd.expectedHash }, owner), e => e instanceof AppError && e.code === "idempotency-conflict");
  db.throwAfterCommit = true; const r = await s.execute(w.id, b.workspace.revision, randomUUID(), cmd, owner); assert.equal(r.replayed, true); assert.equal(r.workspace.receipts.length, 2); assert.equal(r.workspace.ledger.length, 1); db.close();
});
test("workspace listing, reads and owner backups cannot cross membership boundaries", async () => {
  const { db, s, w } = await fixture();
  assert.deepEqual(await s.list(reader), []); await assert.rejects(s.read(w.id, reader), e => e instanceof AppError && e.status === 403);
  let v = await s.execute(w.id, w.revision, randomUUID(), { type: "invite", email: reader.email, role: "reader" }, owner);
  assert.equal((await s.list(reader))[0].role, "invited"); await assert.rejects(s.read(w.id, reader));
  v = await s.execute(w.id, v.workspace.revision, randomUUID(), { type: "join" }, reader);
  assert.equal((await s.read(w.id, reader)).id, w.id); await assert.rejects(s.backup(w.id, reader));
  await s.execute(w.id, v.workspace.revision, randomUUID(), { type: "removeMember", userId: reader.userId }, owner);
  await assert.rejects(s.read(w.id, reader)); assert.deepEqual(await s.list(reader), []); db.close();
});
test("catalog exposes selected packets only; publication and withdrawal are atomic", async () => {
  const { db, s, w } = await fixture(), target = { claimId: w.claims[0].id, expectedHash: current(w.claims[0]).hash };
  assert.deepEqual(await s.catalog(reader), []);
  db.failAfterStatement = 2;
  await assert.rejects(s.execute(w.id, w.revision, randomUUID(), { type: "publishClaim", ...target }, owner));
  assert.deepEqual(await s.catalog(reader), []); assert.equal((await s.read(w.id, owner)).publications.length, 0);
  let v = await s.execute(w.id, w.revision, randomUUID(), { type: "publishClaim", ...target }, owner);
  let catalog = await s.catalog(reader); assert.equal(catalog.length, 1); assert(!canonical(catalog).includes("Private lab name")); assert(!canonical(catalog).includes(owner.email));
  v = await s.execute(w.id, v.workspace.revision, randomUUID(), { type: "reviseClaim", ...target, claim: { ...input, title: "New revision" } }, owner);
  catalog = await s.catalog(reader); assert.equal(catalog[0].stale, true);
  await s.execute(w.id, v.workspace.revision, randomUUID(), { type: "revokePublication", publicationId: v.workspace.publications[0].id }, owner);
  assert.deepEqual(await s.catalog(reader), []); db.close();
});
