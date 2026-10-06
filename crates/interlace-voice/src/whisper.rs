//! whisper.cpp CPU inference. One context at a time. Failures are `None`.

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int};
use std::path::Path;
use std::sync::Mutex;

static CALL: Mutex<()> = Mutex::new(());

unsafe extern "C" {
    fn interlace_whisper_transcribe(
        model_path: *const c_char,
        samples: *const f32,
        n_samples: c_int,
    ) -> *mut c_char;
    fn interlace_whisper_free(text: *mut c_char);
}

pub fn transcribe(pcm: &[f32], weights: &Path) -> Option<String> {
    let _guard = CALL.lock().unwrap_or_else(|err| err.into_inner());
    let path = weights.to_str()?;
    let c_path = CString::new(path).ok()?;
    let n = c_int::try_from(pcm.len()).ok()?;
    if n <= 0 {
        return None;
    }
    // The mutex keeps the C context single-threaded. The pointer is copied
    // before it is freed. `c_path` and `pcm` stay alive for the call.
    let ptr = unsafe { interlace_whisper_transcribe(c_path.as_ptr(), pcm.as_ptr(), n) };
    if ptr.is_null() {
        return None;
    }
    let raw = unsafe { CStr::from_ptr(ptr) }
        .to_string_lossy()
        .into_owned();
    unsafe { interlace_whisper_free(ptr) };
    plain_text(&raw)
}

fn plain_text(raw: &str) -> Option<String> {
    let stripped = strip_angle_tokens(raw);
    let words: Vec<&str> = stripped
        .split_whitespace()
        .filter(|word| !is_control_word(word))
        .collect();
    let text = words.join(" ");
    if text.is_empty() || !text.chars().any(|c| c.is_alphanumeric()) {
        None
    } else {
        Some(text)
    }
}

fn strip_angle_tokens(raw: &str) -> String {
    let mut out = String::with_capacity(raw.len());
    let mut rest = raw;
    while let Some(start) = rest.find("<|") {
        out.push_str(&rest[..start]);
        out.push(' ');
        let after = &rest[start + 2..];
        if let Some(end) = after.find("|>") {
            rest = &after[end + 2..];
        } else {
            rest = &rest[start..];
            break;
        }
    }
    out.push_str(rest);
    out
}

fn is_control_word(word: &str) -> bool {
    let trimmed = word.trim_matches(|c: char| matches!(c, ',' | '.' | '!' | '?' | '"' | '\''));
    if trimmed.len() < 3 || !trimmed.starts_with('[') || !trimmed.ends_with(']') {
        return false;
    }
    trimmed[1..trimmed.len() - 1]
        .chars()
        .all(|c| c.is_ascii_uppercase() || c == '_' || c == ' ')
}
