use std::fs;
use std::io::Read;
use std::process;
use std::time::{SystemTime, UNIX_EPOCH};

use interlace_fixtures::{
    load_pack, write_contacts_csv, write_contacts_vcf, write_mbox, write_takeout_tree,
    write_whatsapp_zip, ContactsGenConfig, MboxGenConfig, TakeoutGenConfig, WaGenConfig, PACK_IDS,
};
use zip::ZipArchive;

fn tmp() -> std::path::PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let p = std::env::temp_dir().join(format!("il-fix-{}-{n}", process::id()));
    let _ = fs::remove_dir_all(&p);
    fs::create_dir_all(&p).unwrap();
    p
}

#[test]
fn five_locale_packs_load() {
    assert_eq!(PACK_IDS.len(), 5);
    for id in PACK_IDS {
        let p = load_pack(id).expect(id);
        assert_eq!(p.id, *id);
        assert!(!p.you_tokens.is_empty());
        assert!(!p.date_time_patterns.is_empty());
    }
}

#[test]
fn whatsapp_zip_deterministic_and_has_chat() {
    let dir = tmp();
    let cfg = WaGenConfig {
        locale: "en-US",
        ios: true,
        with_media: false,
        n_messages: 20,
        n_participants: 2,
        corrupt_line_every: None,
        missing_media_every: None,
        multiline_ratio: 0.0,
        system_every: None,
        seed: 42,
    };
    let a = write_whatsapp_zip(&dir.join("a"), &cfg);
    let b = write_whatsapp_zip(&dir.join("b"), &cfg);
    assert_eq!(fs::read(&a).unwrap(), fs::read(&b).unwrap());
    let mut z = ZipArchive::new(fs::File::open(&a).unwrap()).unwrap();
    let mut chat = z.by_name("_chat.txt").unwrap();
    let mut s = String::new();
    chat.read_to_string(&mut s).unwrap();
    assert!(s.contains("[2024-"), "{s}");
    assert!(s.contains("You:") || s.contains("Person0:"), "{s}");
    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn mbox_escapes_from_in_body() {
    let dir = tmp();
    let path = dir.join("mail.mbox");
    let n = write_mbox(
        &path,
        &MboxGenConfig {
            n_messages: 3,
            seed: 1,
            missing_message_id_every: Some(3),
            escape_from_in_body: true,
            mixed_charsets: true,
        },
    );
    assert_eq!(n, 3);
    let text = fs::read_to_string(&path).unwrap();
    assert!(text.contains(">From someone quoted"));
    assert!(text.contains("ISO-8859-9") || text.contains("windows-1254"));
    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn contacts_vcf_and_csv() {
    let dir = tmp();
    let vcf = dir.join("c.vcf");
    write_contacts_vcf(
        &vcf,
        &ContactsGenConfig {
            n: 2,
            seed: 9,
            with_uid: true,
            with_photo: true,
            empty_fn: false,
        },
    );
    let t = fs::read_to_string(&vcf).unwrap();
    assert!(t.contains("BEGIN:VCARD"));
    assert!(t.contains("UID:"));
    assert!(t.contains("TEL;"));
    write_contacts_csv(
        &dir.join("c.csv"),
        &ContactsGenConfig {
            n: 1,
            seed: 1,
            with_uid: false,
            with_photo: false,
            empty_fn: false,
        },
    );
    let csv = fs::read_to_string(dir.join("c.csv")).unwrap();
    assert!(csv.contains("E-mail 1 - Value"));
    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn takeout_tree_layout() {
    let dir = tmp();
    let root = write_takeout_tree(
        &dir,
        &TakeoutGenConfig {
            n_mail: 2,
            n_contacts: 2,
            seed: 7,
        },
    );
    assert!(root
        .join("Mail/All mail Including Spam and Trash.mbox")
        .is_file());
    assert!(root.join("Contacts/All Contacts.vcf").is_file());
    let _ = fs::remove_dir_all(&dir);
}
