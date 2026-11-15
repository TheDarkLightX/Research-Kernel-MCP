import { env } from "cloudflare:workers";
import { getChatGPTUser } from "@/app/chatgpt-auth";
import { AppError, ResearchStore } from "./store";
import type { Actor } from "./core/model";
export async function authenticatedActor(): Promise<Actor> {
  const user = await getChatGPTUser();
  if (!user) throw new AppError(401, "sign-in-required", "Sign in with ChatGPT to access research memory.");
  return { userId: user.userId, email: user.email.toLowerCase(), name: user.displayName };
}
export function store() {
  if (!env.DB) throw new AppError(503, "storage-unavailable", "Research storage is unavailable. Your unsaved input is preserved; try again shortly.");
  return new ResearchStore(env.DB);
}
export { json, errorResponse, validateOrigin, readJson } from "./http-common";
