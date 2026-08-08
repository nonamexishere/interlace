use interlace_core::db::migrate;
use rusqlite::Connection;

#[test]
fn migrate_empty() {
    let conn = Connection::open_in_memory().expect("memory db");
    migrate(&conn).expect("migrate 0001");

    let mut stmt = conn
        .prepare("PRAGMA compile_options")
        .expect("compile_options");
    let opts: Vec<String> = stmt
        .query_map([], |r| r.get::<_, String>(0))
        .unwrap()
        .map(|r| r.unwrap())
        .collect();
    assert!(
        opts.iter().any(|o| o.contains("ENABLE_FTS5")),
        "bundled sqlite missing ENABLE_FTS5; got {opts:?}"
    );

    let n: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM schema_migrations WHERE version = 1",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(n, 1);

    let tables: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='messages'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(tables, 1);

    migrate(&conn).expect("migrate is idempotent");
}
