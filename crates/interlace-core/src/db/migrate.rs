use rusqlite::Connection;

use super::Result;

const INIT_SQL: &str = include_str!("../../migrations/0001_init.sql");

/// Apply pending numbered SQL migrations. `0001_init.sql` is version 1.
pub fn migrate(conn: &Connection) -> Result<()> {
    let has_migrations: i64 = conn.query_row(
        "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'",
        [],
        |r| r.get(0),
    )?;
    if has_migrations == 0 {
        conn.execute_batch(INIT_SQL)?;
    }
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations(version, name) VALUES (1, '0001_init')",
        [],
    )?;
    Ok(())
}
