use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_core::db::{init_archive, open_archive, LockMode};
use interlace_core::CoreError;

static TMP_SEQ: AtomicU64 = AtomicU64::new(0);

fn tmp_root() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let seq = TMP_SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("interlace-lock-{}-{n}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&p);
    p
}

#[test]
fn exclusive_lock_blocks_second_writer() {
    let root = tmp_root();
    let first = init_archive(&root).expect("init");
    match open_archive(&root, LockMode::Exclusive) {
        Err(CoreError::Lock { .. }) => {}
        Err(other) => panic!("expected Lock, got {other:?}"),
        Ok(_) => panic!("second exclusive lock must fail"),
    }
    drop(first);
    open_archive(&root, LockMode::Exclusive).expect("after drop, EX ok");
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn two_shared_locks_ok() {
    let root = tmp_root();
    let _a = init_archive(&root).expect("init");
    // init holds EX; drop it then take two SH
    drop(_a);
    let s1 = open_archive(&root, LockMode::Shared).expect("sh1");
    let s2 = open_archive(&root, LockMode::Shared).expect("sh2");
    drop(s1);
    drop(s2);
    let _ = std::fs::remove_dir_all(&root);
}
