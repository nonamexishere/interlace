//! Five shipped WhatsApp locale packs + datetime / name / phone helpers.

mod fold;
mod header;
mod media;
mod pack;

pub use fold::{name_fold, name_fold_join, normalize_email, parse_phone, strip_cf};
#[allow(unused_imports)]
pub use header::{
    parse_dt_with_pack, parse_header_line, vote_locale, HeaderFamily, ParsedDt, ParsedHeader,
};
pub use media::{
    is_encryption_banner, is_you_token, looks_like_group_system, match_media, split_sender_body,
    strip_forwarded, strip_title_prefix, title_has_group_prefix, title_looks_like_dm, MediaMatch,
};
pub use pack::{all_packs, load_pack, LocalePack, PACK_IDS};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn match_media_finds_attached_after_caption() {
        let pack = load_pack("tr-TR").unwrap();
        match match_media(
            &pack,
            "hello\n<attached: 00000663-PHOTO-2026-08-08-06-24-05.jpg>",
        ) {
            MediaMatch::File(n) => {
                assert_eq!(n, "00000663-PHOTO-2026-08-08-06-24-05.jpg");
            }
            other => panic!("{other:?}"),
        }
        assert_eq!(
            match_media(&pack, "<attached: sticker.webp>"),
            MediaMatch::File("sticker.webp".into())
        );
    }

    #[test]
    fn unpadded_day_matches_tr_and_de() {
        let tr = load_pack("tr-TR").unwrap();
        let de = load_pack("de-DE").unwrap();
        for dt in [
            "3.08.2025, 02:31:13",
            "26.03.2025, 10:24:07",
            "7.04.2025, 23:21:09",
        ] {
            assert!(parse_dt_with_pack(&tr, dt).is_some(), "tr-TR {dt}");
            assert!(parse_dt_with_pack(&de, dt).is_some(), "de-DE {dt}");
        }
    }

    #[test]
    fn vote_tr_banner_not_de_on_padded_comma() {
        let lines = [
            "[26.03.2025, 10:24:07] Mesajlar ve aramalar uçtan uca şifrelidir",
            "[26.03.2025, 10:24:15] Mustafa: merhaba",
            "[26.03.2025, 10:24:20] Alice: hi",
        ];
        let refs: Vec<&str> = lines.to_vec();
        assert_eq!(
            vote_locale(&refs, Some(HeaderFamily::Ios), None).unwrap(),
            "tr-TR"
        );
    }

    #[test]
    fn vote_de_banner_not_tr_on_padded_comma() {
        let lines = [
            "[26.03.2025, 10:24:07] Nachrichten und Anrufe sind Ende-zu-Ende-verschlüsselt",
            "[26.03.2025, 10:24:15] Mustafa: hallo",
            "[26.03.2025, 10:24:20] Alice: hi",
        ];
        let refs: Vec<&str> = lines.to_vec();
        assert_eq!(
            vote_locale(&refs, Some(HeaderFamily::Ios), None).unwrap(),
            "de-DE"
        );
    }

    #[test]
    fn vote_mixed_unpadded_tr_banner() {
        let lines = [
            "[3.08.2025, 02:31:13] Mesajlar ve aramalar uçtan uca şifrelidir",
            "[26.03.2025, 10:24:07] Mustafa: a",
            "[7.04.2025, 23:21:09] Alice: b",
        ];
        let refs: Vec<&str> = lines.to_vec();
        assert_eq!(
            vote_locale(&refs, Some(HeaderFamily::Ios), None).unwrap(),
            "tr-TR"
        );
    }

    #[test]
    fn vote_english_banner_unpadded_uses_phone_region() {
        let lines = [
            "[3.08.2025, 02:31:13] Messages and calls are end-to-end encrypted",
            "[3.08.2025, 02:31:14] Mustafa: a",
            "[3.08.2025, 02:31:15] Alice: b",
        ];
        let refs: Vec<&str> = lines.to_vec();
        assert_eq!(
            vote_locale(&refs, Some(HeaderFamily::Ios), Some("TR")).unwrap(),
            "tr-TR"
        );
        assert_eq!(
            vote_locale(&refs, Some(HeaderFamily::Ios), Some("DE")).unwrap(),
            "de-DE"
        );
        assert!(vote_locale(&refs, Some(HeaderFamily::Ios), None).is_err());
    }

    #[test]
    fn vote_undated_tr_banner_breaks_tie() {
        let lines = [
            "Mesajlar ve aramalar uçtan uca şifrelidir",
            "[3.08.2025, 02:31:13] Mustafa: a",
            "[3.08.2025, 02:31:15] Alice: b",
        ];
        let refs: Vec<&str> = lines.to_vec();
        assert_eq!(
            vote_locale(&refs, Some(HeaderFamily::Ios), None).unwrap(),
            "tr-TR"
        );
    }
}
