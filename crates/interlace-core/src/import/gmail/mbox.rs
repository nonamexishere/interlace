//! mboxrd record split and From_ unescape.

use std::fs;
use std::path::Path;

use crate::model::*;

pub(super) struct MboxRec<'a> {
    pub start: usize,
    pub end: usize,
    pub raw: &'a [u8],
}

pub(super) fn split_mboxrd(bytes: &[u8]) -> Vec<MboxRec<'_>> {
    // Record start: byte 0 or a newline then `From ` (space, no colon) at
    // column 0. `\nFrom ` and `\r\nFrom ` both match (`\r\nFrom ` contains
    // `\nFrom `). `>From ` is not a separator. No blank line required —
    // Takeout All-mail uses `\nFrom ` between records.
    let mut starts = Vec::new();
    if bytes.starts_with(b"From ") {
        starts.push(0);
    }
    let needle = b"\nFrom ";
    for (i, w) in bytes.windows(needle.len()).enumerate() {
        if w == needle {
            starts.push(i + 1);
        }
    }
    starts.sort_unstable();
    starts.dedup();
    let mut out = Vec::new();
    for (k, &s) in starts.iter().enumerate() {
        let e = starts.get(k + 1).copied().unwrap_or(bytes.len());
        if e > s {
            out.push(MboxRec {
                start: s,
                end: e,
                raw: &bytes[s..e],
            });
        }
    }
    out
}

pub(super) fn split_from_line(raw: &[u8]) -> (Option<String>, Vec<u8>) {
    if let Some(pos) = raw.iter().position(|&b| b == b'\n') {
        let line = String::from_utf8_lossy(&raw[..pos])
            .trim_end_matches('\r')
            .to_string();
        let rest = raw[pos + 1..].to_vec();
        if line.starts_with("From ") {
            return (Some(line), rest);
        }
    }
    (None, raw.to_vec())
}

pub(super) fn unescape_mboxrd(rfc: Vec<u8>) -> Vec<u8> {
    let mut out = Vec::with_capacity(rfc.len());
    for line in rfc.split_inclusive(|&b| b == b'\n') {
        if let Some(stripped) = strip_mboxrd_gt(line) {
            out.extend_from_slice(stripped);
        } else {
            out.extend_from_slice(line);
        }
    }
    out
}

fn strip_mboxrd_gt(line: &[u8]) -> Option<&[u8]> {
    // ^(>+)From  lose one leading >
    if !line.starts_with(b">") {
        return None;
    }
    let mut i = 0;
    while i < line.len() && line[i] == b'>' {
        i += 1;
    }
    if line
        .get(i..)
        .map(|s| s.starts_with(b"From "))
        .unwrap_or(false)
        && i >= 1
    {
        Some(&line[1..])
    } else {
        None
    }
}

pub(super) fn header_block_len(rfc: &[u8]) -> usize {
    if let Some(p) = find_sub(rfc, b"\n\n") {
        p + 2
    } else if let Some(p) = find_sub(rfc, b"\r\n\r\n") {
        p + 4
    } else {
        rfc.len()
    }
}

fn find_sub(hay: &[u8], needle: &[u8]) -> Option<usize> {
    hay.windows(needle.len()).position(|w| w == needle)
}

pub(super) fn excerpt(raw: &[u8]) -> String {
    String::from_utf8_lossy(&raw[..raw.len().min(200)]).into_owned()
}

pub(super) fn read_prefix(path: &Path, n: usize) -> Result<Vec<u8>, CoreError> {
    use std::io::Read;
    let mut f = fs::File::open(path)?;
    let mut buf = vec![0u8; n];
    let got = f.read(&mut buf)?;
    buf.truncate(got);
    Ok(buf)
}
