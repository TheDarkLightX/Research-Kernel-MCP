import { sha256 } from "./hash";
import { CHECKER_SOURCE_SHA256 } from "./checker-pin";
import { KERNEL_SOURCE_SHA256 } from "./kernel-pin";
import { canonical, createWorkspace, roleFor, type Actor, type Workspace } from "./core/model";
import { transition } from "./core/transition";
import { commandSchema } from "./core/validation";

export class AppError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}
type WorkspaceRow = { id: string; name: string; owner: string; revision: number; state: string; genesis: string; last_commit: string; updated_at: string };
export class ResearchStore {
  constructor(private db: D1Database) {}
  async list(actor: Actor) {
    const rows = await this.db.prepare(
      "SELECT id,name,revision,state FROM workspaces WHERE owner=? OR EXISTS (SELECT 1 FROM json_each(workspaces.state,'$.members') AS m WHERE json_extract(m.value,'$.userId')=?) OR EXISTS (SELECT 1 FROM json_each(workspaces.state,'$.invitations') AS i WHERE json_extract(i.value,'$.email')=?) ORDER BY updated_at DESC LIMIT 50"
    ).bind(actor.userId, actor.userId, actor.email.toLowerCase()).all<WorkspaceRow>();
    return rows.results.map(r => {
      const s: Workspace = JSON.parse(r.state);
      return { id: r.id, name: r.name, revision: r.revision, role: roleFor(s, actor) ?? "invited", claims: s.claims.length };
    });
  }
  private async row(id: string) {
    const row = await this.db.prepare("SELECT * FROM workspaces WHERE id=?").bind(id).first<WorkspaceRow>();
    if (!row) throw new AppError(404, "not-found", "Workspace does not exist or is inaccessible.");
    return row;
  }
  async read(id: string, actor: Actor): Promise<Workspace> {
    const row = await this.row(id), state: Workspace = JSON.parse(row.state);
    if (!roleFor(state, actor)) throw new AppError(403, "forbidden", "Workspace membership is required.");
    return state;
  }
  async create(name: string, requestId: string, actor: Actor) {
    const id = sha256(canonical(["workspace", actor.userId, requestId]));
    const existing = await this.db.prepare("SELECT * FROM workspaces WHERE id=?").bind(id).first<WorkspaceRow>();
    if (existing) {
      if (existing.owner !== actor.userId || existing.name !== name) throw new AppError(409, "idempotency-conflict", "Request ID was already used with different input.");
      return JSON.parse(existing.state) as Workspace;
    }
    const state = createWorkspace(id, name, actor), at = new Date().toISOString();
    const saved = await this.db.prepare("INSERT INTO workspaces (id,name,owner,revision,state,genesis,last_commit,updated_at) SELECT ?,?,?,0,?,?,'genesis',? WHERE (SELECT count(*) FROM workspaces WHERE owner=?) < 20")
      .bind(id, name, actor.userId, canonical(state), canonical(state), at, actor.userId).run();
    if (saved.meta.changes !== 1) throw new AppError(409, "capacity", "At most 20 pilot workspaces per owner.");
    return state;
  }
  async execute(id: string, expectedRevision: number, requestId: string, raw: unknown, actor: Actor) {
    const parsed = commandSchema.safeParse(raw);
    if (!parsed.success) throw new AppError(400, "invalid-command", parsed.error.issues.map(i => i.message).slice(0, 3).join("; "));
    const command = parsed.data, row = await this.row(id), before: Workspace = JSON.parse(row.state);
    if (command.type !== "join" && !roleFor(before, actor)) throw new AppError(403, "forbidden", "Workspace membership is required.");
    const commitId = sha256(canonical([id, actor.userId, requestId])), encodedCommand = canonical(command);
    const prior = await this.db.prepare("SELECT command,result FROM workspace_commits WHERE id=? AND workspace_id=? AND actor=?").bind(commitId, id, actor.userId).first<{ command: string; result: string }>();
    if (prior) {
      if (prior.command !== encodedCommand) throw new AppError(409, "idempotency-conflict", "Request ID was already used with a different command.");
      return { workspace: await this.read(id, actor), result: JSON.parse(prior.result), replayed: true };
    }
    if (before.revision !== expectedRevision) throw new AppError(409, "stale-workspace", "Workspace changed. Reload before saving.");
    const now = new Date().toISOString();
    const context = { actor, id: commitId, now, checkerSourceHash: CHECKER_SOURCE_SHA256 };
    const decision = transition(before, command, context, sha256);
    if (decision.decision === "reject") throw new AppError(decision.code === "forbidden" ? 403 : 422, decision.code, decision.message);
    const encodedState = canonical(decision.state);
    // D1 batch is transactional. The conditional insert records exactly the CAS-winning candidate.
    const statements = [
      this.db.prepare("UPDATE workspaces SET revision=?,state=?,last_commit=?,updated_at=? WHERE id=? AND revision=?")
        .bind(decision.state.revision, encodedState, commitId, now, id, decision.expectedRevision),
      this.db.prepare("INSERT INTO workspace_commits (id,workspace_id,revision,actor,command,result,state_hash,previous_hash,checker_source_hash,kernel_source_hash,context,at) SELECT ?,?,?,?,?,?,?,?,?,?,?,? WHERE EXISTS (SELECT 1 FROM workspaces WHERE id=? AND revision=? AND last_commit=?)")
        .bind(commitId, id, decision.state.revision, actor.userId, encodedCommand, canonical(decision.result), sha256(encodedState), sha256(row.state), CHECKER_SOURCE_SHA256, KERNEL_SOURCE_SHA256, canonical(context), now, id, decision.state.revision, commitId),
    ];
    for (const packet of decision.state.publications) {
      const old = before.publications.find(p => p.id === packet.id);
      if (!old) statements.push(this.db.prepare("INSERT INTO publication_packages (id,workspace_id,packet,revoked,at) SELECT ?,?,?,?,? WHERE EXISTS (SELECT 1 FROM workspaces WHERE id=? AND last_commit=?)").bind(packet.id, id, canonical(packet), packet.revoked ? 1 : 0, now, id, commitId));
      else if (packet.revoked !== old.revoked) statements.push(this.db.prepare("UPDATE publication_packages SET revoked=?,packet=? WHERE id=? AND workspace_id=? AND EXISTS (SELECT 1 FROM workspaces WHERE id=? AND last_commit=?)").bind(packet.revoked ? 1 : 0, canonical(packet), packet.id, id, id, commitId));
    }
    let batch: D1Result[];
    try { batch = await this.db.batch(statements); }
    catch (e) {
      // A simultaneous retry may already have committed this exact candidate.
      const saved = await this.db.prepare("SELECT command,result FROM workspace_commits WHERE id=? AND workspace_id=? AND actor=?").bind(commitId, id, actor.userId).first<{ command: string; result: string }>();
      if (saved?.command === encodedCommand) return { workspace: await this.read(id, actor), result: JSON.parse(saved.result), replayed: true };
      throw e;
    }
    if (batch[0].meta.changes !== 1 || batch[1].meta.changes !== 1) throw new AppError(409, "stale-workspace", "Another change won the commit. Reload before retrying.");
    return { workspace: decision.state, result: decision.result, replayed: false };
  }
  async catalog(_actor: Actor) {
    // Every catalog packet is selected explicitly by an owner; private workspace state is never returned.
    const rows = await this.db.prepare("SELECT p.packet, EXISTS (SELECT 1 FROM json_each(w.state,'$.claims') AS c WHERE (json_extract(c.value,'$.needsReview')=1 OR json_extract(c.value,'$.revisions[#-1].hash')<>json_extract(p.packet,'$.claim.hash')) AND json_extract(c.value,'$.id')=json_extract(p.packet,'$.claimId')) AS stale FROM publication_packages p JOIN workspaces w ON p.workspace_id=w.id WHERE p.revoked=0 ORDER BY p.at DESC LIMIT 20").all<{ packet: string; stale: number }>();
    return rows.results.map(row => ({ packet: JSON.parse(row.packet), stale: !!row.stale }));
  }
  async backup(id: string, actor: Actor) {
    const reads = await this.db.batch([
      this.db.prepare("SELECT * FROM workspaces WHERE id=?").bind(id),
      this.db.prepare("SELECT * FROM workspace_commits WHERE workspace_id=? ORDER BY revision").bind(id),
    ]);
    const row = reads[0].results[0] as WorkspaceRow | undefined;
    if (!row) throw new AppError(404, "not-found", "Workspace does not exist or is inaccessible.");
    const state: Workspace = JSON.parse(row.state);
    if (roleFor(state, actor) !== "owner") throw new AppError(403, "forbidden", "Only the owner can export the full private workspace.");
    const content = { schema: "rk-private-backup/1", genesis: JSON.parse(row.genesis), workspace: state, commits: reads[1].results, authority: "backup-only", kernelSourceHash: KERNEL_SOURCE_SHA256 };
    return { ...content, hash: sha256(canonical(content)) };
  }
}
