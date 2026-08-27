use std::path::PathBuf;

use crate::db::{open_archive, LockMode};
use crate::{
    person_list, person_merge, person_timeline, person_undo, person_unlink, PersonMergeOpts,
};

use super::common::{resolve_path, CliError};
use super::PersonCmd;

pub(super) fn cmd_person(
    path: Option<PathBuf>,
    json: bool,
    verbose: bool,
    cmd: PersonCmd,
) -> Result<(), CliError> {
    match cmd {
        PersonCmd::List => {
            let root = resolve_path(path)?;
            let arch = open_archive(&root, LockMode::Shared)?;
            let rows = person_list(&arch)?;
            if json {
                println!("{}", serde_json::to_string(&rows).unwrap());
            } else {
                for p in rows {
                    let act = p.last_activity_at.as_deref().unwrap_or("-");
                    let self_mark = if p.is_self { "  (self)" } else { "" };
                    println!("{}\t{}{}\t{}", p.id, p.display_name, self_mark, act);
                }
            }
        }
        PersonCmd::Show { id, include_groups } => {
            let root = resolve_path(path)?;
            let arch = open_archive(&root, LockMode::Shared)?;
            let name: String = arch.conn.query_row(
                "SELECT display_name FROM persons WHERE id=?1 AND tombstoned_at IS NULL",
                [id],
                |r| r.get(0),
            )?;
            let mut stmt = arch.conn.prepare(
                "SELECT i.id, i.platform, i.kind, i.value_normalized, i.display_name
                 FROM person_identities pi JOIN identities i ON i.id = pi.identity_id
                 WHERE pi.person_id = ?1",
            )?;
            let idents: Vec<serde_json::Value> = stmt
                .query_map([id], |r| {
                    Ok(serde_json::json!({
                        "id": r.get::<_, i64>(0)?,
                        "platform": r.get::<_, String>(1)?,
                        "kind": r.get::<_, String>(2)?,
                        "value": r.get::<_, String>(3)?,
                        "display_name": r.get::<_, Option<String>>(4)?,
                    }))
                })?
                .collect::<Result<Vec<_>, _>>()?;
            let tl = person_timeline(&arch, id, include_groups, 20)?;
            if json {
                let mut hits = Vec::new();
                for h in &tl {
                    hits.push(serde_json::json!({
                        "message_id": h.message_id,
                        "sent_at": h.sent_at,
                        "snippet": if verbose { &h.snippet } else { "[redacted]" },
                    }));
                }
                println!(
                    "{}",
                    serde_json::json!({
                        "id": id,
                        "display_name": name,
                        "identities": idents,
                        "timeline": hits,
                    })
                );
            } else {
                println!("person {id}  {name}");
                println!("identities: {idents:?}");
                for h in tl {
                    println!("  msg {}  {}", h.message_id, h.snippet.replace('\n', " "));
                }
            }
        }
        PersonCmd::Merge { a, b, keep } => {
            let root = resolve_path(path)?;
            let mut arch = open_archive(&root, LockMode::Exclusive)?;
            let survivor = person_merge(&mut arch, a, b, PersonMergeOpts { keep })?;
            let ev: i64 = arch.conn.query_row(
                "SELECT id FROM identity_link_events WHERE op='merge_persons' ORDER BY id DESC LIMIT 1",
                [],
                |r| r.get(0),
            )?;
            println!("merged → {survivor} event_id={ev}");
        }
        PersonCmd::Unlink { identity } => {
            let root = resolve_path(path)?;
            let mut arch = open_archive(&root, LockMode::Exclusive)?;
            person_unlink(&mut arch, identity)?;
            println!("unlinked identity {identity}");
        }
        PersonCmd::Undo { event } => {
            let root = resolve_path(path)?;
            let mut arch = open_archive(&root, LockMode::Exclusive)?;
            person_undo(&mut arch, event)?;
            println!("undo event {event}");
        }
    }
    Ok(())
}
