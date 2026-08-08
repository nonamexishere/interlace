use std::fs::File;
use std::io::Write;
use std::path::{Path, PathBuf};

use zip::write::SimpleFileOptions;
use zip::{CompressionMethod, ZipWriter};

use crate::datetime::{format_pattern, stamp};
use crate::locale::load_pack;
use crate::rng::Rng;

#[derive(Debug, Clone)]
pub struct WaGenConfig {
    pub locale: &'static str,
    pub ios: bool,
    pub with_media: bool,
    pub n_messages: usize,
    pub n_participants: usize,
    pub corrupt_line_every: Option<usize>,
    pub missing_media_every: Option<usize>,
    pub multiline_ratio: f32,
    pub system_every: Option<usize>,
    pub seed: u64,
}

/// Write a synthetic WhatsApp export zip. Deterministic for a given `seed`.
pub fn write_whatsapp_zip(dir: &Path, cfg: &WaGenConfig) -> PathBuf {
    std::fs::create_dir_all(dir).expect("mkdir");
    let pack = load_pack(cfg.locale).expect("locale");
    let kind = if cfg.ios { "ios" } else { "android" };
    let zip_path = dir.join(format!("whatsapp-{}-{}.zip", cfg.locale, kind));
    let file = File::create(&zip_path).expect("zip create");
    let mut zip = ZipWriter::new(file);
    let opts = SimpleFileOptions::default().compression_method(CompressionMethod::Deflated);

    let chat_name = if cfg.ios {
        "_chat.txt".to_string()
    } else {
        let title = pack
            .title_prefixes_dm
            .first()
            .cloned()
            .unwrap_or_else(|| "WhatsApp Chat with ".into());
        format!("{title}Alice.txt")
    };

    let mut rng = Rng::new(cfg.seed);
    let you = pack
        .you_tokens
        .first()
        .cloned()
        .unwrap_or_else(|| "You".into());
    let mut names = vec![you];
    for i in 0..cfg.n_participants.saturating_sub(1) {
        names.push(format!("Person{i}"));
    }

    let pattern = pack
        .date_time_patterns
        .first()
        .expect("date_time_patterns")
        .as_str();
    let mut body = String::new();
    if let Some(banner) = pack.system_encryption.first() {
        let (y, mo, d, h, mi, s) = stamp(0);
        let dt = format_pattern(pattern, y, mo, d, h, mi, s);
        body.push_str(&header_line(cfg.ios, &dt, banner, true));
        body.push('\n');
    }

    for i in 1..=cfg.n_messages {
        if cfg.corrupt_line_every.is_some_and(|n| n > 0 && i % n == 0) {
            body.push_str("??? not-a-header garbage line\n");
        }
        let (y, mo, d, h, mi, s) = stamp(i);
        let dt = format_pattern(pattern, y, mo, d, h, mi, s);
        if cfg.system_every.is_some_and(|n| n > 0 && i % n == 0) {
            let sys = pack
                .system_created_group
                .first()
                .map(|s| format!("Person0 {s}"))
                .unwrap_or_else(|| "Person0 created group".into());
            body.push_str(&header_line(cfg.ios, &dt, &sys, true));
            body.push('\n');
            continue;
        }
        let sender = names[rng.usize(names.len())].as_str();
        let mut text = format!("msg-{i} hello from {sender}");
        let fname = format!("IMG-{i:04}.jpg");
        if cfg.with_media && i % 7 == 0 {
            let omitted = cfg.missing_media_every.is_some_and(|n| n > 0 && i % n == 0);
            if omitted {
                text = pack
                    .media_omitted
                    .first()
                    .cloned()
                    .unwrap_or_else(|| "<Media omitted>".into());
            } else if let Some(alt) = pack.file_attached_alt.first() {
                text = alt.replace("{filename}", &fname);
                zip.start_file(&fname, opts).expect("media entry");
                zip.write_all(b"\xFF\xD8fakejpeg").expect("media bytes");
            } else {
                text = format!("{fname} (file attached)");
                zip.start_file(&fname, opts).expect("media entry");
                zip.write_all(b"\xFF\xD8fakejpeg").expect("media bytes");
            }
        }
        body.push_str(&header_line(
            cfg.ios,
            &dt,
            &format!("{sender}: {text}"),
            false,
        ));
        body.push('\n');
        if rng.f32() < cfg.multiline_ratio {
            body.push_str("continuation line\n");
        }
    }

    zip.start_file(&chat_name, opts).expect("chat entry");
    zip.write_all(body.as_bytes()).expect("chat bytes");
    zip.finish().expect("zip finish");
    zip_path
}

fn header_line(ios: bool, dt: &str, rest: &str, system: bool) -> String {
    let _ = system;
    if ios {
        format!("[{dt}] {rest}")
    } else {
        format!("{dt} - {rest}")
    }
}
