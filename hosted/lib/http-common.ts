import { AppError } from "./store";
export function json(value: unknown, status = 200) {
  return Response.json(value, { status, headers: { "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff" } });
}
export function errorResponse(e: unknown) {
  if (e instanceof AppError) return json({ error: e.message, code: e.code }, e.status);
  console.error("Research Kernel request failed", e instanceof Error ? e.message : "unknown");
  return json({ error: "The request could not complete. Your input is preserved.", code: "internal-error" }, 500);
}
export function validateOrigin(request: Request, mcp = false) {
  const origin = request.headers.get("Origin");
  if (origin && origin !== new URL(request.url).origin && !(mcp && ["https://chatgpt.com", "https://chat.openai.com"].includes(origin))) throw new AppError(403, "invalid-origin", "This origin is not allowed.");
}
export async function readJson(request: Request): Promise<unknown> {
  if (!request.headers.get("Content-Type")?.toLowerCase().includes("application/json")) throw new AppError(415, "invalid-content-type", "Use application/json.");
  const reader = request.body?.getReader();
  if (!reader) throw new AppError(400, "invalid-json", "Request body is required.");
  let size = 0; const parts: Uint8Array[] = [];
  while (true) {
    const { value, done } = await reader.read(); if (done) break;
    size += value.length; if (size > 250000) { await reader.cancel(); throw new AppError(413, "request-too-large", "Request exceeds 250 KB."); }
    parts.push(value);
  }
  const data = new Uint8Array(size); let offset = 0; for (const p of parts) { data.set(p, offset); offset += p.length; }
  try { return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(data)); }
  catch { throw new AppError(400, "invalid-json", "Request is not valid UTF-8 JSON."); }
}
