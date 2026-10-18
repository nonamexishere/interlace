//! Parent SIGKILL at a `rename` / `unlink` under the archive. The interpose
//! lives in this test module. Product code is not paused.

use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::{Mutex, MutexGuard, OnceLock};
use std::thread;
use std::time::{Duration, Instant};

const WNOHANG: i32 = 1;
const WUNTRACED: i32 = 2;
const SIGKILL: i32 = 9;

extern "C" {
    fn waitpid(pid: i32, status: *mut i32, options: i32) -> i32;
    fn kill(pid: i32, sig: i32) -> i32;
}

pub fn child_enter() -> bool {
    std::env::var_os("INTERLACE_CRASH_CHILD").is_some()
}

/// Hold for the whole `#[test]`.
///
/// These binaries run tests on many threads, and `kill_at_seam` forks. The
/// child inherits every open file until exec, and `flock` stays held on that
/// fd after the parent closes it. A sibling that then opens its archive sees
/// `Lock { pid: <this process> }`. One guard at a time keeps a spawn from
/// overlapping another test's lock fd.
pub fn one_test_at_a_time() -> MutexGuard<'static, ()> {
    static ONE: Mutex<()> = Mutex::new(());
    ONE.lock().unwrap_or_else(|err| err.into_inner())
}

pub struct KillSpec<'a> {
    pub test_name: &'a str,
    pub mode: &'a str,
    pub root: &'a Path,
    pub target: &'a str,
    pub extra: &'a [(&'a str, &'a str)],
}

pub fn kill_at_seam(spec: KillSpec<'_>) {
    let dylib = interpose_lib();
    let arm = spec.root.join("tmp").join("crash-arm");
    let marker = spec.root.join("tmp").join("crash-marker");
    let log = spec.root.join("tmp").join("crash-log");
    let _ = fs::remove_file(&arm);
    let _ = fs::remove_file(&marker);
    let _ = fs::remove_file(&log);
    let exe = std::env::current_exe().expect("current_exe");
    let mut cmd = Command::new(exe);
    cmd.arg(spec.test_name)
        .arg("--exact")
        .arg("--test-threads=1")
        .env("INTERLACE_CRASH_CHILD", "1")
        .env("INTERLACE_CRASH_MODE", spec.mode)
        .env("INTERLACE_CRASH_ROOT", spec.root)
        .env("INTERLACE_CRASH_ARM", &arm)
        .env("INTERLACE_CRASH_MARKER", &marker)
        .env("INTERLACE_CRASH_LOG", &log)
        .env("INTERLACE_CRASH_TARGET", spec.target)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    if cfg!(target_os = "macos") {
        cmd.env("DYLD_INSERT_LIBRARIES", &dylib);
    } else {
        cmd.env("LD_PRELOAD", &dylib);
    }
    for (key, value) in spec.extra {
        cmd.env(key, value);
    }
    let mut child = cmd.spawn().expect("spawn crash child");
    let stdout = child.stdout.take();
    let stderr = child.stderr.take();
    let pid = child.id() as i32;
    // Reaped here. Drop must not wait a second time.
    std::mem::forget(child);
    let stdout_handle = thread::spawn(move || read_pipe(stdout));
    let stderr_handle = thread::spawn(move || read_pipe(stderr));
    let _guard = KillOnDrop(pid);

    let start = Instant::now();
    #[allow(unused_assignments)]
    let mut hit = false;
    loop {
        if marker.is_file() {
            hit = true;
            unsafe { kill(pid, SIGKILL) };
            break;
        }
        match poll_status(pid, false) {
            Poll::Running => {}
            Poll::Stopped => {
                hit = true;
                unsafe { kill(pid, SIGKILL) };
                break;
            }
            Poll::Exited(code) => {
                let (out, err) = join_pipes(stdout_handle, stderr_handle);
                panic!(
                    "{} child exited {code} before the file change\nstdout:\n{out}\nstderr:\n{err}\nlog:\n{}",
                    spec.test_name,
                    read_text(&log)
                );
            }
            Poll::Signaled(sig) => {
                let (out, err) = join_pipes(stdout_handle, stderr_handle);
                panic!(
                    "{} child signal {sig} before the file change\nstdout:\n{out}\nstderr:\n{err}\nlog:\n{}",
                    spec.test_name,
                    read_text(&log)
                );
            }
            Poll::Error(err) => panic!("{} waitpid: {err}", spec.test_name),
        }
        if start.elapsed() > Duration::from_secs(30) {
            unsafe { kill(pid, SIGKILL) };
            let (out, err) = join_pipes(stdout_handle, stderr_handle);
            panic!(
                "{} timed out before the file change\nstdout:\n{out}\nstderr:\n{err}\nlog:\n{}",
                spec.test_name,
                read_text(&log)
            );
        }
        thread::sleep(Duration::from_millis(5));
    }

    let status = reap_killed(pid);
    // Pipes close after death. Join before the guard's second reap.
    let (out, err) = join_pipes(stdout_handle, stderr_handle);
    std::mem::forget(_guard);
    match status {
        Poll::Signaled(9) if hit => {}
        other => panic!(
            "{} expected SIGKILL at the seam, got {other:?}\nmarker:\n{}\nstdout:\n{out}\nstderr:\n{err}\nlog:\n{}",
            spec.test_name,
            read_text(&marker),
            read_text(&log)
        ),
    }
}

fn reap_killed(pid: i32) -> Poll {
    let start = Instant::now();
    loop {
        match poll_status(pid, false) {
            Poll::Running => {}
            Poll::Stopped => {
                unsafe { kill(pid, SIGKILL) };
            }
            other => return other,
        }
        if start.elapsed() > Duration::from_secs(5) {
            return Poll::Error("reap timed out".into());
        }
        thread::sleep(Duration::from_millis(5));
    }
}

struct KillOnDrop(i32);

impl Drop for KillOnDrop {
    fn drop(&mut self) {
        if self.0 <= 0 {
            return;
        }
        unsafe { kill(self.0, SIGKILL) };
        let mut status = 0;
        unsafe { waitpid(self.0, &mut status, 0) };
    }
}

#[derive(Debug)]
enum Poll {
    Running,
    Stopped,
    Exited(i32),
    Signaled(i32),
    Error(String),
}

fn poll_status(pid: i32, block: bool) -> Poll {
    let flags = if block {
        WUNTRACED
    } else {
        WNOHANG | WUNTRACED
    };
    loop {
        let mut status = 0;
        let got = unsafe { waitpid(pid, &mut status, flags) };
        if got < 0 {
            let err = std::io::Error::last_os_error();
            if err.kind() == std::io::ErrorKind::Interrupted {
                continue;
            }
            return Poll::Error(err.to_string());
        }
        if got == 0 {
            return Poll::Running;
        }
        let low = status & 0o177;
        if low == 0o177 {
            return Poll::Stopped;
        }
        if low == 0 {
            return Poll::Exited((status >> 8) & 0xff);
        }
        return Poll::Signaled(low);
    }
}

fn read_pipe(pipe: Option<impl Read>) -> Vec<u8> {
    let mut buf = Vec::new();
    if let Some(mut pipe) = pipe {
        let _ = pipe.read_to_end(&mut buf);
    }
    buf
}

fn join_pipes(
    stdout: thread::JoinHandle<Vec<u8>>,
    stderr: thread::JoinHandle<Vec<u8>>,
) -> (String, String) {
    let out = stdout.join().unwrap_or_default();
    let err = stderr.join().unwrap_or_default();
    (clip(&out), clip(&err))
}

fn clip(bytes: &[u8]) -> String {
    let text = String::from_utf8_lossy(bytes);
    let text = text.trim();
    const MAX: usize = 4000;
    if text.len() <= MAX {
        text.to_string()
    } else {
        format!("...{}", &text[text.len() - MAX..])
    }
}

fn read_text(path: &Path) -> String {
    fs::read_to_string(path).unwrap_or_default()
}

fn interpose_lib() -> PathBuf {
    static LIB: OnceLock<PathBuf> = OnceLock::new();
    LIB.get_or_init(|| {
        let dir = std::env::temp_dir().join(format!("il-crash-kill-{}", std::process::id()));
        fs::create_dir_all(&dir).expect("interpose dir");
        let src = dir.join("interpose.c");
        let lib = dir.join(if cfg!(target_os = "macos") {
            "libcrashkill.dylib"
        } else {
            "libcrashkill.so"
        });
        fs::write(&src, INTERPOSE_C).expect("write interpose.c");
        let mut cc = Command::new("cc");
        if cfg!(target_os = "macos") {
            cc.args(["-dynamiclib", "-o"]);
        } else {
            cc.args(["-shared", "-fPIC", "-o"]);
        }
        cc.arg(&lib).arg(&src);
        if !cfg!(target_os = "macos") {
            cc.arg("-ldl");
        }
        let out = cc.output().expect("spawn cc");
        if !out.status.success() {
            panic!(
                "cc interpose failed: {}",
                String::from_utf8_lossy(&out.stderr)
            );
        }
        fs::canonicalize(&lib).unwrap_or(lib)
    })
    .clone()
}

const INTERPOSE_C: &str = r#"
#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#ifdef __APPLE__
#define DYLD_INTERPOSE(_replacement, _replacee) \
    __attribute__((used)) static struct { const void *replacement; const void *replacee; } \
    _interpose_##_replacee __attribute__((section("__DATA,__interpose"))) = { \
        (const void *)(unsigned long)&_replacement, \
        (const void *)(unsigned long)&_replacee }
#endif

static void log_op(const char *op, const char *a, const char *b) {
    const char *log = getenv("INTERLACE_CRASH_LOG");
    int fd;
    char buf[8192];
    int n;
    if (!log || !log[0]) return;
    fd = open(log, O_WRONLY | O_CREAT | O_APPEND, 0644);
    if (fd < 0) return;
    n = snprintf(buf, sizeof buf, "%s %s -> %s\n", op, a ? a : "-", b ? b : "-");
    if (n > 0) {
        if (n > (int)sizeof buf) n = (int)sizeof buf;
        (void)write(fd, buf, (size_t)n);
    }
    (void)close(fd);
}

static void halt(const char *why, const char *a, const char *b) {
    const char *marker = getenv("INTERLACE_CRASH_MARKER");
    if (marker && marker[0]) {
        int fd = open(marker, O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (fd >= 0) {
            char buf[8192];
            int n = snprintf(buf, sizeof buf, "%s\n%s\n%s\n", why, a ? a : "", b ? b : "");
            if (n > 0) {
                if (n > (int)sizeof buf) n = (int)sizeof buf;
                (void)write(fd, buf, (size_t)n);
            }
            (void)close(fd);
        }
    }
    log_op("STOP", why, a);
    raise(SIGSTOP);
    kill(getpid(), SIGKILL);
    _exit(125);
}

static int armed(void) {
    const char *arm = getenv("INTERLACE_CRASH_ARM");
    if (!arm || !arm[0]) return 0;
    return access(arm, F_OK) == 0;
}

static int has_prefix(const char *path, const char *root, const char *rest) {
    size_t n;
    if (!path || !root) return 0;
    n = strlen(root);
    if (strncmp(path, root, n) != 0) return 0;
    return strncmp(path + n, rest, strlen(rest)) == 0;
}

static int under_cas(const char *path, const char *root) {
    return has_prefix(path, root, "/cas/");
}

static int is_live_cas(const char *path, const char *root) {
    size_t n;
    const char *p;
    if (!has_prefix(path, root, "/cas")) return 0;
    n = strlen(root);
    p = path + n + 4;
    while (*p == '/') p++;
    return *p == '\0';
}

static int basename_is(const char *path, const char *want) {
    const char *base;
    if (!path || !want || !want[0]) return 0;
    base = path;
    for (const char *p = path; *p; p++) {
        if (*p == '/') base = p + 1;
    }
    return strcmp(base, want) == 0;
}

static int want_rename(const char *from, const char *to) {
    const char *mode = getenv("INTERLACE_CRASH_MODE");
    const char *root = getenv("INTERLACE_CRASH_ROOT");
    const char *target = getenv("INTERLACE_CRASH_TARGET");
    if (!armed() || !mode || !root || !to) return 0;
    if (strcmp(mode, "reattach") == 0) {
        return under_cas(to, root) && basename_is(to, target);
    }
    if (strcmp(mode, "snapshot") == 0) {
        char live[4096];
        struct stat st;
        if (!is_live_cas(to, root)) return 0;
        snprintf(live, sizeof live, "%s/archive.sqlite", root);
        if (access(live, F_OK) != 0) return 0;
        if (from && stat(from, &st) == 0 && !S_ISDIR(st.st_mode)) return 0;
        return 1;
    }
    return 0;
}

static int want_unlink(const char *path) {
    const char *mode = getenv("INTERLACE_CRASH_MODE");
    const char *root = getenv("INTERLACE_CRASH_ROOT");
    const char *target = getenv("INTERLACE_CRASH_TARGET");
    if (!armed() || !mode || !root || !path) return 0;
    if (strcmp(mode, "reclaim") != 0 && strcmp(mode, "gc") != 0) return 0;
    return under_cas(path, root) && basename_is(path, target);
}

static int call_rename(const char *from, const char *to) {
#ifdef __APPLE__
    return rename(from, to);
#else
    static int (*real_fn)(const char *, const char *) = 0;
    if (!real_fn) real_fn = (int (*)(const char *, const char *))dlsym(RTLD_NEXT, "rename");
    return real_fn(from, to);
#endif
}

static int call_renameat(int fromfd, const char *from, int tofd, const char *to) {
#ifdef __APPLE__
    return renameat(fromfd, from, tofd, to);
#else
    static int (*real_fn)(int, const char *, int, const char *) = 0;
    if (!real_fn)
        real_fn = (int (*)(int, const char *, int, const char *))dlsym(RTLD_NEXT, "renameat");
    return real_fn(fromfd, from, tofd, to);
#endif
}

static int call_unlink(const char *path) {
#ifdef __APPLE__
    return unlink(path);
#else
    static int (*real_fn)(const char *) = 0;
    if (!real_fn) real_fn = (int (*)(const char *))dlsym(RTLD_NEXT, "unlink");
    return real_fn(path);
#endif
}

static int call_unlinkat(int fd, const char *path, int flags) {
#ifdef __APPLE__
    return unlinkat(fd, path, flags);
#else
    static int (*real_fn)(int, const char *, int) = 0;
    if (!real_fn) real_fn = (int (*)(int, const char *, int))dlsym(RTLD_NEXT, "unlinkat");
    return real_fn(fd, path, flags);
#endif
}

static int handle_rename(const char *from, const char *to) {
    if (armed()) log_op("rename", from, to);
    if (want_rename(from, to)) halt("rename-before", from, to);
    return call_rename(from, to);
}

static int handle_renameat(int fromfd, const char *from, int tofd, const char *to) {
    if (armed()) log_op("renameat", from, to);
    if (want_rename(from, to)) halt("renameat-before", from, to);
    return call_renameat(fromfd, from, tofd, to);
}

static int handle_unlink(const char *path) {
    const char *mode = getenv("INTERLACE_CRASH_MODE");
    int stop = want_unlink(path);
    int rc;
    if (armed()) log_op("unlink", path, "-");
    if (stop && mode && strcmp(mode, "reclaim") == 0) halt("unlink-before", path, "");
    rc = call_unlink(path);
    if (stop && mode && strcmp(mode, "gc") == 0 && rc == 0) halt("unlink-after", path, "");
    return rc;
}

static int handle_unlinkat(int fd, const char *path, int flags) {
    const char *mode = getenv("INTERLACE_CRASH_MODE");
    int stop = want_unlink(path);
    int rc;
    if (armed()) log_op("unlinkat", path, "-");
    if (stop && mode && strcmp(mode, "reclaim") == 0) halt("unlinkat-before", path, "");
    rc = call_unlinkat(fd, path, flags);
    if (stop && mode && strcmp(mode, "gc") == 0 && rc == 0) halt("unlinkat-after", path, "");
    return rc;
}

#ifdef __APPLE__
int crash_rename(const char *from, const char *to) { return handle_rename(from, to); }
int crash_renameat(int fromfd, const char *from, int tofd, const char *to) {
    return handle_renameat(fromfd, from, tofd, to);
}
int crash_unlink(const char *path) { return handle_unlink(path); }
int crash_unlinkat(int fd, const char *path, int flags) {
    return handle_unlinkat(fd, path, flags);
}
DYLD_INTERPOSE(crash_rename, rename);
DYLD_INTERPOSE(crash_renameat, renameat);
DYLD_INTERPOSE(crash_unlink, unlink);
DYLD_INTERPOSE(crash_unlinkat, unlinkat);
#else
int rename(const char *from, const char *to) { return handle_rename(from, to); }
int renameat(int fromfd, const char *from, int tofd, const char *to) {
    return handle_renameat(fromfd, from, tofd, to);
}
int unlink(const char *path) { return handle_unlink(path); }
int unlinkat(int fd, const char *path, int flags) { return handle_unlinkat(fd, path, flags); }
#endif
"#;
