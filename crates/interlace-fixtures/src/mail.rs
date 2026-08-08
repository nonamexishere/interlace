use std::fs;
use std::path::{Path, PathBuf};

use crate::rng::Rng;

#[derive(Debug, Clone)]
pub struct MboxGenConfig {
    pub n_messages: usize,
    pub seed: u64,
    pub missing_message_id_every: Option<usize>,
    pub escape_from_in_body: bool,
    pub mixed_charsets: bool,
}

/// Write an mboxrd file. Returns message count.
pub fn write_mbox(path: &Path, cfg: &MboxGenConfig) -> u64 {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("mkdir");
    }
    let mut rng = Rng::new(cfg.seed);
    let mut out = String::new();
    for i in 0..cfg.n_messages {
        out.push_str(&format!(
            "From tester@example.com Sat Jan 01 00:00:{:02} 2024\n",
            i % 60
        ));
        let from = format!("alice+tag{}@gmail.com", rng.usize(3));
        out.push_str(&format!("From: {from}\n"));
        out.push_str("To: bob@example.com\n");
        out.push_str(&format!("Subject: synthetic {i}\n"));
        if !cfg
            .missing_message_id_every
            .is_some_and(|n| n > 0 && (i + 1) % n == 0)
        {
            out.push_str(&format!("Message-ID: <msg-{i}@example.com>\n"));
        }
        out.push_str("MIME-Version: 1.0\n");
        let cs = if cfg.mixed_charsets {
            match i % 3 {
                0 => "utf-8",
                1 => "ISO-8859-9",
                _ => "windows-1254",
            }
        } else {
            "utf-8"
        };
        out.push_str(&format!("Content-Type: text/plain; charset={cs}\n\n"));
        out.push_str(&format!("Hello body {i}\n"));
        if cfg.escape_from_in_body {
            out.push_str(">From someone quoted in the body\n");
        }
        out.push('\n');
    }
    fs::write(path, out).expect("write mbox");
    cfg.n_messages as u64
}

#[derive(Debug, Clone)]
pub struct TakeoutGenConfig {
    pub n_mail: usize,
    pub n_contacts: usize,
    pub seed: u64,
}

/// Extracted Takeout/ tree (happy path).
pub fn write_takeout_tree(dir: &Path, cfg: &TakeoutGenConfig) -> PathBuf {
    let root = dir.join("Takeout");
    fs::create_dir_all(root.join("Mail")).unwrap();
    fs::create_dir_all(root.join("Contacts")).unwrap();
    write_mbox(
        &root.join("Mail/All mail Including Spam and Trash.mbox"),
        &MboxGenConfig {
            n_messages: cfg.n_mail,
            seed: cfg.seed,
            missing_message_id_every: None,
            escape_from_in_body: true,
            mixed_charsets: false,
        },
    );
    crate::contacts::write_contacts_vcf(
        &root.join("Contacts/All Contacts.vcf"),
        &crate::contacts::ContactsGenConfig {
            n: cfg.n_contacts,
            seed: cfg.seed ^ 0x9e37,
            with_uid: true,
            with_photo: false,
            empty_fn: false,
        },
    );
    root
}
