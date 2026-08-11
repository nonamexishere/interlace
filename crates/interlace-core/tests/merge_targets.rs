//! Merge-target picker filter (#127). Name-only people; no numeric id field.
//!
//! Not a Phase 1 matrix ID. Do not add to test_plan.json.
//!
//! Contract impl must add in `people`:
//! `merge_targets(people, selected_id, allow_self, query)`
//! — drop the selected person; drop `is_self` unless `allow_self`;
//! keep a name only when `display_name` contains `query` under casefold.

use interlace_core::people::{merge_targets, PersonSummary};

fn person(id: i64, display_name: &str, is_self: bool) -> PersonSummary {
    PersonSummary {
        id,
        display_name: display_name.to_string(),
        is_self,
        last_activity_at: None,
        preview: None,
    }
}

/// Placeholders Ada / Ali / Me (self).
fn roster() -> Vec<PersonSummary> {
    vec![
        person(1, "Me", true),
        person(2, "Ada", false),
        person(3, "Ali", false),
    ]
}

fn target_ids(selected_id: i64, allow_self: bool, query: &str) -> Vec<i64> {
    merge_targets(&roster(), selected_id, allow_self, query)
        .into_iter()
        .map(|p| p.id)
        .collect()
}

fn target_names(selected_id: i64, allow_self: bool, query: &str) -> Vec<String> {
    merge_targets(&roster(), selected_id, allow_self, query)
        .into_iter()
        .map(|p| p.display_name.clone())
        .collect()
}

#[test]
fn excludes_selected_person() {
    assert_eq!(target_ids(2, false, "a"), [3]);
    assert_eq!(target_names(2, false, "a"), ["Ali".to_string()]);
    assert_eq!(target_ids(3, false, "a"), [2]);
    assert_eq!(target_names(3, false, "a"), ["Ada".to_string()]);
}

#[test]
fn hides_self_unless_allow_self() {
    assert!(target_ids(2, false, "me").is_empty());
    assert!(target_ids(2, false, "Me").is_empty());
    assert_eq!(target_ids(2, true, "me"), [1]);
    assert_eq!(target_names(2, true, "ME"), ["Me".to_string()]);
}

#[test]
fn name_substring_is_casefold() {
    assert_eq!(target_names(1, false, "ada"), ["Ada".to_string()]);
    assert_eq!(target_names(1, false, "ADA"), ["Ada".to_string()]);
    assert_eq!(target_names(1, false, "ali"), ["Ali".to_string()]);
    assert_eq!(
        target_names(1, false, "a"),
        ["Ada".to_string(), "Ali".to_string()]
    );
    assert_eq!(target_names(1, false, "da"), ["Ada".to_string()]);
}

#[test]
fn query_does_not_match_numeric_id() {
    assert!(target_ids(1, false, "2").is_empty());
    assert!(target_ids(1, false, "3").is_empty());
}

#[test]
fn selected_self_stays_out_when_allow_self() {
    assert_eq!(
        target_names(1, true, ""),
        ["Ada".to_string(), "Ali".to_string()]
    );
    assert!(target_ids(1, true, "me").is_empty());
}

#[test]
fn pick_ali_by_name_while_ada_selected() {
    assert_eq!(target_names(2, false, "ali"), ["Ali".to_string()]);
    assert!(!target_ids(2, false, "ali").contains(&2));
    assert!(!target_ids(2, false, "ali").contains(&1));
}
