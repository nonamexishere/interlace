use rusqlite::Connection;

use super::Result;

const INIT_SQL: &str = include_str!("../../migrations/0001_init.sql");

/// Numbered files after 0001.
const MIGRATIONS: &[(i64, &str, &str)] = &[(
    2,
    "0002_raw_cas_hash",
    include_str!("../../migrations/0002_raw_cas_hash.sql"),
)];

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
    for (version, name, sql) in MIGRATIONS {
        let applied: i64 = conn.query_row(
            "SELECT COUNT(*) FROM schema_migrations WHERE version = ?1",
            [version],
            |r| r.get(0),
        )?;
        if applied == 0 {
            conn.execute_batch("BEGIN IMMEDIATE")?;
            let step = (|| -> Result<()> {
                conn.execute_batch(sql)?;
                conn.execute(
                    "INSERT INTO schema_migrations(version, name) VALUES (?1, ?2)",
                    rusqlite::params![version, name],
                )?;
                Ok(())
            })();
            match step {
                Ok(()) => conn.execute_batch("COMMIT")?,
                Err(e) => {
                    let _ = conn.execute_batch("ROLLBACK");
                    return Err(e);
                }
            }
        }
    }
    Ok(())
}
