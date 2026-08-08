use std::fs;
use std::path::Path;

#[derive(Debug, Clone)]
pub struct ContactsGenConfig {
    pub n: usize,
    pub seed: u64,
    pub with_uid: bool,
    pub with_photo: bool,
    pub empty_fn: bool,
}

pub fn write_contacts_vcf(path: &Path, cfg: &ContactsGenConfig) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).unwrap();
    }
    let mut out = String::new();
    for i in 0..cfg.n {
        out.push_str("BEGIN:VCARD\nVERSION:3.0\n");
        if cfg.with_uid {
            out.push_str(&format!("UID:syn-{:04x}-{:x}\n", i, cfg.seed & 0xffff));
        }
        if cfg.empty_fn {
            out.push_str("FN:\n");
        } else {
            out.push_str(&format!("FN:Alice {i}\n"));
            out.push_str(&format!("N:Smith;Alice {i};;;\n"));
        }
        out.push_str(&format!("TEL;TYPE=CELL:+90532111{:04}\n", 1000 + i));
        out.push_str(&format!("EMAIL;TYPE=INTERNET:alice{i}@gmail.com\n"));
        if cfg.with_photo {
            out.push_str("PHOTO;ENCODING=b;TYPE=JPEG:/9j/4AAQ\n");
        }
        out.push_str("END:VCARD\n");
    }
    fs::write(path, out).unwrap();
}

pub fn write_contacts_csv(path: &Path, cfg: &ContactsGenConfig) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).unwrap();
    }
    let mut out =
        String::from("First Name,Middle Name,Last Name,E-mail 1 - Value,Phone 1 - Value\n");
    for i in 0..cfg.n {
        if cfg.empty_fn {
            out.push_str(&format!(",,,alice{i}@gmail.com,+90532111{:04}\n", 1000 + i));
        } else {
            out.push_str(&format!(
                "Alice,,Smith{i},alice{i}@gmail.com,+90532111{:04}\n",
                1000 + i
            ));
        }
    }
    fs::write(path, out).unwrap();
}
