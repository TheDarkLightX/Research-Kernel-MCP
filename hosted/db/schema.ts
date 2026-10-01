import { integer, sqliteTable, text, index, uniqueIndex } from "drizzle-orm/sqlite-core";
export const workspaces = sqliteTable("workspaces", {
  id: text("id").primaryKey(), name: text("name").notNull(), owner: text("owner").notNull(),
  revision: integer("revision").notNull(), state: text("state").notNull(), genesis: text("genesis").notNull(),
  lastCommit: text("last_commit").notNull(), updatedAt: text("updated_at").notNull(),
}, t => [index("workspace_owner_idx").on(t.owner)]);
export const commits = sqliteTable("workspace_commits", {
  id: text("id").primaryKey(), workspaceId: text("workspace_id").notNull().references(() => workspaces.id),
  revision: integer("revision").notNull(), actor: text("actor").notNull(), command: text("command").notNull(), result: text("result").notNull(),
  stateHash: text("state_hash").notNull(), previousHash: text("previous_hash").notNull(),
  checkerSourceHash: text("checker_source_hash").notNull(), kernelSourceHash: text("kernel_source_hash").notNull(), context: text("context").notNull(), at: text("at").notNull(),
}, t => [uniqueIndex("workspace_revision_idx").on(t.workspaceId, t.revision)]);
export const packages = sqliteTable("publication_packages", {
  id: text("id").primaryKey(), workspaceId: text("workspace_id").notNull().references(() => workspaces.id),
  packet: text("packet").notNull(), revoked: integer("revoked").notNull(), at: text("at").notNull(),
}, t => [index("publication_catalog_idx").on(t.revoked, t.at)]);
