import { DatabaseSync } from "node:sqlite";
import { readdirSync, readFileSync } from "node:fs";
export class SqliteD1 {
  readonly db: DatabaseSync;
  failAfterStatement = -1; throwAfterCommit = false;
  constructor(path = ":memory:", migrate = true) {
    this.db = new DatabaseSync(path); this.db.exec("PRAGMA foreign_keys=ON");
    if (migrate) for (const file of readdirSync("drizzle").filter(n => n.endsWith(".sql")).sort()) this.db.exec(readFileSync("drizzle/" + file, "utf8").replaceAll("--> statement-breakpoint", ""));
  }
  prepare(sql: string) {
    const database = this.db;
    const make = (params: unknown[]) => ({
      bind: (...values: unknown[]) => make(values),
      first: async (column?: string) => { const row = database.prepare(sql).get(...params as never[]) ?? null; return column && row ? row[column] : row; },
      all: async () => ({ results: database.prepare(sql).all(...params as never[]), success: true, meta: {} }),
      run: async () => run(),
      _run: () => run(),
    });
    const run = (params: unknown[] = []) => {
      if (/^SELECT/i.test(sql.trim())) return { success: true, results: database.prepare(sql).all(...params as never[]), meta: { changes: 0 } };
      const r = database.prepare(sql).run(...params as never[]); return { success: true, results: [], meta: { changes: Number(r.changes) } };
    };
    const wrapped = (params: unknown[]): any => {
      const q = make(params); q.run = async () => run(params); q._run = () => run(params); q.bind = (...values: unknown[]) => wrapped(values); return q;
    };
    return wrapped([]);
  }
  async batch(statements: any[]) {
    this.db.exec("BEGIN IMMEDIATE");
    try {
      const results = statements.map((s, i) => { const r = s._run(); if (i === this.failAfterStatement) { this.failAfterStatement = -1; throw new Error("Injected storage failure."); } return r; });
      this.db.exec("COMMIT");
      if (this.throwAfterCommit) { this.throwAfterCommit = false; throw new Error("Injected response failure after commit."); }
      return results;
    } catch (e) { try { this.db.exec("ROLLBACK"); } catch {} throw e; }
  }
  port() { return this as unknown as D1Database; }
  close() { this.db.close(); }
}
