import { transition } from "./core/transition";
import { canonical, type Context, type Workspace } from "./core/model";
import { sha256 } from "./hash";
import { KERNEL_SOURCE_SHA256 } from "./kernel-pin";
import { CHECKER_SOURCE_SHA256 } from "./checker-pin";
type Commit = { id: string; workspace_id: string; revision: number; actor: string; command: string; result: string; state_hash: string; previous_hash: string; checker_source_hash: string; kernel_source_hash: string; context: string; at: string };
export function verifyReplay(genesis: Workspace, commits: Commit[], expected: Workspace) {
  let state = structuredClone(genesis);
  if (state.revision !== 0 || state.audit.length !== 0) throw new Error("Invalid genesis.");
  for (const entry of commits) {
    if (entry.kernel_source_hash !== KERNEL_SOURCE_SHA256 || entry.checker_source_hash !== CHECKER_SOURCE_SHA256) throw new Error("Replay needs the original functional-core and checker source version.");
    const ctx: Context = JSON.parse(entry.context);
    if (entry.workspace_id !== state.id || entry.revision !== state.revision + 1 || entry.previous_hash !== sha256(canonical(state)) || entry.actor !== ctx.actor.userId || entry.id !== ctx.id || entry.at !== ctx.now || entry.checker_source_hash !== ctx.checkerSourceHash) throw new Error("Commit lineage mismatch.");
    const decision = transition(state, JSON.parse(entry.command), ctx, sha256);
    if (decision.decision !== "accept" || entry.state_hash !== sha256(canonical(decision.state)) || entry.result !== canonical(decision.result)) throw new Error("Commit replay mismatch.");
    state = decision.state;
  }
  if (canonical(state) !== canonical(expected)) throw new Error("Recovered snapshot mismatch.");
  return { verified: true, revisions: state.revision, stateHash: sha256(canonical(state)), authority: "journal-consistency-only" };
}
