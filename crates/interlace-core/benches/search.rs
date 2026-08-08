//! Search SLA bench. Default 10k (PR / S4 proxy). Nightly: INTERLACE_BENCH=1M|10M.
//! Writes pipeline/stages/07-bench/OUT.json. Does not generate 1M in PR CI.

use std::env;
use std::fs;
use std::path::PathBuf;
use std::time::Instant;

use interlace_core::db::init_archive;
use interlace_core::search::{index_import_run, search};
use interlace_core::SearchQuery;

fn n_messages() -> usize {
    match env::var("INTERLACE_BENCH").ok().as_deref() {
        Some("1M") => 1_000_000,
        Some("10M") => 10_000_000,
        _ => 10_000,
    }
}

fn mode_label() -> String {
    env::var("INTERLACE_BENCH").unwrap_or_else(|_| "PR".into())
}

fn percentile(sorted: &[f64], p: f64) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    let idx = ((sorted.len() as f64 - 1.0) * p).round() as usize;
    sorted[idx.min(sorted.len() - 1)]
}

fn time_query(arch: &interlace_core::db::Archive, q: &str, n: usize) -> Vec<f64> {
    let sq = SearchQuery {
        q: q.into(),
        ..SearchQuery::default()
    };
    for _ in 0..3 {
        let _ = search(arch, &sq);
    }
    let mut ms = Vec::with_capacity(n);
    for _ in 0..n {
        let t = Instant::now();
        let _ = search(arch, &sq).expect("search");
        ms.push(t.elapsed().as_secs_f64() * 1000.0);
    }
    ms
}

fn main() {
    let n = n_messages();
    let mode = mode_label();
    let tmp = env::temp_dir().join(format!("interlace-bench-{mode}-{n}"));
    let _ = fs::remove_dir_all(&tmp);
    let arch = init_archive(&tmp).expect("init");

    arch.conn
        .execute(
            "INSERT INTO sources(kind, label, origin_path) VALUES ('gmail_mbox', 'bench', '/bench.mbox')",
            [],
        )
        .unwrap();
    let src = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO import_runs(source_id, status) VALUES (?1, 'done')",
            [src],
        )
        .unwrap();
    let run = arch.conn.last_insert_rowid();
    arch.conn
        .execute(
            "INSERT INTO conversations(platform, kind, native_id, title)
             VALUES ('gmail', 'email_thread', 'gmail-bench', 'bench')",
            [],
        )
        .unwrap();
    let conv = arch.conn.last_insert_rowid();

    {
        let tx = arch.conn.unchecked_transaction().unwrap();
        let mut stmt = tx
            .prepare(
                "INSERT INTO messages(
                    conversation_id, source_id, import_run_id, sent_at, sent_at_precision,
                    kind, body_text, idempotency_key
                 ) VALUES (?1, ?2, ?3, '2024-03-15T14:32:00Z', 'second', 'text', ?4, ?5)",
            )
            .unwrap();
        for i in 0..n {
            let body = if i == 0 {
                "Gidiyoruz İstanbul planted-s1".to_string()
            } else if i == 1 {
                "Yol ISLAK planted-s2".to_string()
            } else if i % 3 == 0 {
                format!("merhaba yarın msg-{i}")
            } else {
                format!("hello unique-{i} body")
            };
            stmt.execute(rusqlite::params![conv, src, run, body, format!("k{i}")])
                .unwrap();
        }
        drop(stmt);
        tx.commit().unwrap();
    }
    index_import_run(&arch, run).expect("index");

    let product = ["istanbul", "ıslak", "islak", "hello"];
    let mut all = Vec::new();
    let mut per_q = Vec::new();
    for q in product {
        let samples = time_query(&arch, q, 5);
        let mut s = samples.clone();
        s.sort_by(|a, b| a.partial_cmp(b).unwrap());
        per_q.push(serde_json::json!({
            "q": q,
            "p50_ms": percentile(&s, 0.50),
            "p95_ms": percentile(&s, 0.95),
        }));
        all.extend(samples);
    }
    all.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let p50 = percentile(&all, 0.50);
    let p95 = percentile(&all, 0.95);

    let hdf_samples = time_query(&arch, "merhaba AND yarın", 5);
    let mut hdf = hdf_samples;
    hdf.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let high_df = serde_json::json!({
        "query": "merhaba AND yarın",
        "p50_ms": percentile(&hdf, 0.50),
        "p95_ms": percentile(&hdf, 0.95),
        "caveat": "Spike 1: almost every TR doc can match; discarded as corpus artifact for the 200ms gate. Recorded, not folded into p95_ms.",
    });

    let db = tmp.join("archive.sqlite");
    let du = fs::metadata(&db).map(|m| m.len()).unwrap_or(0);

    let out = serde_json::json!({
        "n_messages": n,
        "mode": mode,
        "p50_ms": p50,
        "p95_ms": p95,
        "queries": per_q,
        "high_df": high_df,
        "archive_sqlite_bytes": du,
    });

    let dest = env::var("INTERLACE_BENCH_OUT")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("../../pipeline/stages/07-bench/OUT.json")
        });
    if let Some(parent) = dest.parent() {
        fs::create_dir_all(parent).ok();
    }
    fs::write(&dest, serde_json::to_string_pretty(&out).unwrap()).unwrap();
    println!(
        "bench n={n} mode={mode} p50_ms={p50:.3} p95_ms={p95:.3} wrote {}",
        dest.display()
    );
    let _ = fs::remove_dir_all(&tmp);
}
