import { commandSchema } from "./core/validation";
import { current, claimStatus, type Workspace, type Command } from "./core/model";
type Registry = { registerTool: (tool: { name: string; description: string; inputSchema: object; annotations: object; execute: (v: unknown) => unknown }, options: { signal: AbortSignal }) => void | Promise<void> };
export function registerResearchTools(actions: { read: () => Workspace | null; select: (id: string) => void; execute: (cmd: Command) => Promise<unknown> }) {
  const registry = (document as Document & { modelContext?: Registry }).modelContext;
  if (!registry) return;
  const controller = new AbortController();
  const tools = [
    { name: "read_research_memory", description: "Read the selected workspace's claim summaries and current revision.", inputSchema: { type: "object", properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true, untrustedContentHint: true }, execute: (input: unknown) => { if (!input || typeof input !== "object" || Object.keys(input).length) throw new Error("Expected an empty object."); const w = actions.read(); return w ? { workspaceId: w.id, revision: w.revision, claims: w.claims.map(c => ({ id: c.id, title: current(c).title, revisionHash: current(c).hash, status: claimStatus(w, c) })) } : { workspace: null }; } },
    { name: "open_research_claim", description: "Open an existing claim in the visible research record panel.", inputSchema: { type: "object", properties: { claimId: { type: "string" } }, required: ["claimId"], additionalProperties: false }, annotations: { readOnlyHint: true, untrustedContentHint: true }, execute: (input: unknown) => { const v = input as { claimId?: unknown }; if (!v || typeof v.claimId !== "string" || Object.keys(v).some(k => k !== "claimId")) throw new Error("Provide a claimId."); actions.select(v.claimId); return { openedClaimId: v.claimId }; } },
    { name: "run_bounded_research_check", description: "Run the selected claim's bounded recipe and save a revision-bound checker receipt.", inputSchema: { type: "object", properties: { claimId: { type: "string" }, expectedHash: { type: "string", pattern: "^[a-f0-9]{64}$" } }, required: ["claimId", "expectedHash"], additionalProperties: false }, annotations: { readOnlyHint: false, untrustedContentHint: true }, execute: async (input: unknown) => { const v = input as object; const command = commandSchema.parse({ ...v, type: "checkClaim" }); return actions.execute(command); } },
  ];
  for (const tool of tools) { try { Promise.resolve(registry.registerTool(tool, { signal: controller.signal })).catch(() => {}); } catch {} }
  return () => controller.abort();
}
