use std::path::PathBuf;

use crate::db::{open_archive, LockMode};
use crate::{search, SearchQuery};

use super::common::{resolve_path, CliError};
use super::{AttachmentArg, KindArg, PlatArg};

#[allow(clippy::too_many_arguments)]
pub(super) fn cmd_search(
    path: Option<PathBuf>,
    json: bool,
    verbose: bool,
    query: String,
    person: Option<i64>,
    from: Option<String>,
    to: Option<String>,
    platform: Option<PlatArg>,
    kind: Option<KindArg>,
    attachment: Option<AttachmentArg>,
    include_groups: bool,
    limit: u32,
) -> Result<(), CliError> {
    let root = resolve_path(path)?;
    let arch = open_archive(&root, LockMode::Shared)?;
    let q = SearchQuery {
        q: query,
        person_id: person,
        from,
        to,
        platform: platform.map(Into::into),
        conversation_id: None,
        conversation_kind: kind.map(Into::into),
        attachment_filter: attachment.map(Into::into),
        include_groups,
        limit,
    };
    let hits = search(&arch, &q)?;
    if json {
        let mut arr = Vec::new();
        for h in hits {
            let snippet = if verbose {
                h.snippet.clone()
            } else {
                "[redacted]".into()
            };
            arr.push(serde_json::json!({
                "message_id": h.message_id,
                "sent_at": h.sent_at,
                "conversation_id": h.conversation_id,
                "subject": h.subject,
                "snippet": snippet,
                "score": h.score,
            }));
        }
        println!("{}", serde_json::to_string(&arr).unwrap());
    } else {
        for h in hits {
            println!(
                "{}  conv={}  {}",
                h.message_id,
                h.conversation_id,
                h.snippet.replace('\n', " ")
            );
        }
    }
    Ok(())
}
