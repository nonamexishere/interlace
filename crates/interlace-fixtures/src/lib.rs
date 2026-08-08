//! Synthetic exports for Interlace tests. Unpublished. No real user data.

mod contacts;
mod datetime;
mod locale;
mod mail;
mod rng;
mod whatsapp;

pub use contacts::{write_contacts_csv, write_contacts_vcf, ContactsGenConfig};
pub use locale::{load_pack, LocalePack, PACK_IDS};
pub use mail::{write_mbox, write_takeout_tree, MboxGenConfig, TakeoutGenConfig};
pub use whatsapp::{write_whatsapp_zip, WaGenConfig};
