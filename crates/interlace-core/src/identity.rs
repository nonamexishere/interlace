//! Identity resolve / merge / undo / review (PR8).

mod auto;
mod helpers;
mod merge;
mod review;
mod score;

pub use auto::resolve_run;
pub use merge::{person_merge, person_undo, person_unlink};
pub use review::{review_list, review_resolve, review_resolve_selected, review_show};
pub use score::name_score;
