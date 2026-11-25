import type { LakebasePool } from "@databricks/appkit";
import { migrations } from "./migrations.ts";

// Arbitrary constant so concurrent app instances don't run migrations twice.
const MIGRATION_LOCK_ID = 7_340_001;

/** Apply pending migrations, each in its own transaction. Safe to run on every start. */
export async function migrate(pool: LakebasePool): Promise<void> {
  const client = await pool.connect();
  try {
    await client.query("SELECT pg_advisory_lock($1)", [MIGRATION_LOCK_ID]);
    await client.query(`
      CREATE SCHEMA IF NOT EXISTS app;
      CREATE TABLE IF NOT EXISTS app.schema_migrations (
        id         TEXT PRIMARY KEY,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
      );
    `);
    const { rows } = await client.query<{ id: string }>("SELECT id FROM app.schema_migrations");
    const applied = new Set(rows.map((r) => r.id));

    for (const m of migrations) {
      if (applied.has(m.id)) continue;
      try {
        await client.query("BEGIN");
        await client.query(m.sql);
        await client.query("INSERT INTO app.schema_migrations (id) VALUES ($1)", [m.id]);
        await client.query("COMMIT");
        console.log(`[migrate] applied ${m.id}`);
      } catch (err) {
        await client.query("ROLLBACK");
        throw new Error(`Migration ${m.id} failed: ${(err as Error).message}`);
      }
    }
  } finally {
    await client.query("SELECT pg_advisory_unlock($1)", [MIGRATION_LOCK_ID]).catch(() => {});
    client.release();
  }
}
