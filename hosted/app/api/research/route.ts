import { z } from "zod";
import { authenticatedActor, store, json, errorResponse, readJson, validateOrigin } from "@/lib/http";
import { AppError } from "@/lib/store";
export const dynamic = "force-dynamic";
const id = z.string().min(1).max(100), requestId = z.string().uuid();
const createSchema = z.object({ action: z.literal("createWorkspace"), name: z.string().trim().min(3).max(100), requestId }).strict();
const mutationSchema = z.object({ action: z.literal("command"), workspaceId: id, expectedRevision: z.number().int().min(0), requestId, command: z.unknown() }).strict();
export async function GET(request: Request) {
  try {
    const actor = await authenticatedActor(), s = store(), url = new URL(request.url);
    if (url.searchParams.get("catalog") === "1") return json({ catalog: await s.catalog(actor) });
    const workspaceId = url.searchParams.get("workspace");
    if (workspaceId) {
      if (url.searchParams.get("backup") === "1") return json(await s.backup(workspaceId, actor));
      return json({ workspace: await s.read(workspaceId, actor), actor });
    }
    return json({ workspaces: await s.list(actor), actor });
  } catch (e) { return errorResponse(e); }
}
export async function POST(request: Request) {
  try {
    validateOrigin(request);
    const actor = await authenticatedActor(), raw = await readJson(request), s = store();
    const create = createSchema.safeParse(raw);
    if (create.success) return json({ workspace: await s.create(create.data.name, create.data.requestId, actor) }, 201);
    const mutation = mutationSchema.safeParse(raw);
    if (!mutation.success) throw new AppError(400, "invalid-request", "Provide a valid workspace, revision, UUID request ID and command.");
    const v = mutation.data;
    return json(await s.execute(v.workspaceId, v.expectedRevision, v.requestId, v.command, actor));
  } catch (e) { return errorResponse(e); }
}
