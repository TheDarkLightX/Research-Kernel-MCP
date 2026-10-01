import { handleMcp } from "@/lib/mcp-handler";
import { authenticatedActor, store } from "@/lib/http";
export const dynamic = "force-dynamic";
const handler = (request: Request) => handleMcp(request, { authenticate: authenticatedActor, store });
export const POST = handler;
export const GET = handler;
export const DELETE = handler;
