use std::path::PathBuf;

use crate::db::{open_archive, LockMode};
use crate::{review_resolve, review_show};

use super::common::{resolve_path, CliError};
use super::ReviewCmd;

fn platform_label(p: &str) -> &str {
    match p {
        "whatsapp" => "WhatsApp",
        "gmail" => "Gmail",
        "contacts" => "Contacts",
        "owner" => "Me",
        other => other,
    }
}

fn print_review_panel(label: &str, panel: &serde_json::Value) {
    let name = panel["display_name"].as_str().unwrap_or("—");
    let plats: Vec<&str> = panel["platforms"]
        .as_array()
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str().map(platform_label))
                .collect()
        })
        .unwrap_or_default();
    let title = if plats.is_empty() {
        name.to_string()
    } else {
        format!("{name} ({})", plats.join(", "))
    };
    let count = panel["message_count"].as_i64().unwrap_or(0);
    println!("{label}: {title}");
    if let Some(idents) = panel["identifiers"].as_array() {
        for id in idents {
            let kind = id["kind"].as_str().unwrap_or("?");
            let norm = id["value_normalized"].as_str().unwrap_or("");
            println!("  {kind}: {norm}");
        }
    }
    println!(
        "  {} {}",
        count,
        if count == 1 { "message" } else { "messages" }
    );
    let samples = panel["samples"].as_array();
    if samples.map(|s| s.is_empty()).unwrap_or(true) {
        println!("  No messages on this side");
        return;
    }
    for s in samples.unwrap() {
        let at = s["sent_at"].as_str().unwrap_or("no date");
        let body = s["body_text"].as_str().unwrap_or("");
        println!("  {at} · {body}");
    }
}

fn print_review_show(out: &serde_json::Value) {
    let rev = &out["review"];
    println!(
        "id={} status={} score={} {}",
        rev["id"],
        rev["status"].as_str().unwrap_or(""),
        rev["score"],
        rev["reason"].as_str().unwrap_or("")
    );
    if let Some(ev) = out["evidence"].as_array() {
        for e in ev {
            println!(
                "  {} · {} · {}",
                e["type"].as_str().unwrap_or(""),
                e["score"],
                e["detail"].as_str().unwrap_or("")
            );
        }
    }
    let sides = out["sides"].as_array().filter(|a| !a.is_empty());
    if let Some(sides) = sides {
        for (i, panel) in sides.iter().enumerate() {
            print_review_panel(&format!("side {}", i + 1), panel);
        }
    } else {
        print_review_panel("left", &out["left"]);
        print_review_panel("right", &out["right"]);
    }
}

pub(super) fn cmd_review(
    path: Option<PathBuf>,
    json: bool,
    cmd: ReviewCmd,
) -> Result<(), CliError> {
    match cmd {
        ReviewCmd::List => {
            let root = resolve_path(path)?;
            let arch = open_archive(&root, LockMode::Shared)?;
            let mut stmt = arch.conn.prepare(
                "SELECT id, suggested_score, reason_summary, left_identity_id, right_person_id
                 FROM merge_review_queue WHERE status='open' ORDER BY suggested_score DESC, id",
            )?;
            let rows: Vec<serde_json::Value> = stmt
                .query_map([], |r| {
                    Ok(serde_json::json!({
                        "id": r.get::<_, i64>(0)?,
                        "score": r.get::<_, f64>(1)?,
                        "reason": r.get::<_, String>(2)?,
                        "left_identity_id": r.get::<_, i64>(3)?,
                        "right_person_id": r.get::<_, Option<i64>>(4)?,
                    }))
                })?
                .collect::<Result<Vec<_>, _>>()?;
            if json {
                println!("{}", serde_json::to_string(&rows).unwrap());
            } else {
                for r in rows {
                    println!(
                        "id={} score={} {}  identity:{}  person:{:?}",
                        r["id"],
                        r["score"],
                        r["reason"].as_str().unwrap_or(""),
                        r["left_identity_id"],
                        r["right_person_id"]
                    );
                }
            }
        }
        ReviewCmd::Show { id } => {
            let root = resolve_path(path)?;
            let arch = open_archive(&root, LockMode::Shared)?;
            let out = review_show(&arch, id)?;
            if json {
                println!("{}", serde_json::to_string_pretty(&out).unwrap());
            } else {
                print_review_show(&out);
            }
        }
        ReviewCmd::Accept { id } => {
            let root = resolve_path(path)?;
            let mut arch = open_archive(&root, LockMode::Exclusive)?;
            review_resolve(&mut arch, id, true)?;
            println!("accepted review {id}");
        }
        ReviewCmd::Reject { id } => {
            let root = resolve_path(path)?;
            let mut arch = open_archive(&root, LockMode::Exclusive)?;
            review_resolve(&mut arch, id, false)?;
            println!("status=rejected; matcher will skip this pair");
        }
    }
    Ok(())
}
