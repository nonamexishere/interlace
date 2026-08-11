# Import WhatsApp

Interlace reads **official WhatsApp chat export ZIP** files. It does not log
into WhatsApp and never invents JIDs.

## Supported files

| Platform | Typical contents |
| --- | --- |
| **iOS** | `_chat.txt` at zip root (or one level down) + optional media |
| **Android** | exactly one `*.txt` such as `WhatsApp Chat with Alice.txt` + optional media |

Both **with media** and **without media** exports are supported. A text-only
export followed later by a with-media re-export of the same chat **upgrades**
attachments onto the same `messages.id` (W9). The idempotency key does **not**
include the media filename.

Unsupported: `msgstore.db` / `*.crypt14` backups.

## Archive vs export path

`--path` is the **archive directory** (global). The ZIP is the positional export:

```bash
interlace --path ~/Interlace import whatsapp ./chat.zip
interlace import whatsapp ./chat.zip   # uses last-archive-path
```

Do not pass the ZIP to `--path`.

## Locale detection

The first ~50 dated headers vote across the five shipped packs:

`en-US`, `en-GB`, `tr-TR`, `de-DE`, `pt-BR`.

Day/month may be 1 or 2 digits (`3.08.2025` and `26.03.2025`). One pack is
used for the whole file. A datetime tie (common for Turkish vs German comma
dates) is broken by the chat’s native language tokens (encryption banner,
`Siz`/`Du`, media-omitted wording), then by the archive `--phone-region`
(`TR` → `tr-TR`). Still tied or no match — pass `--locale`.

A 0.1.0 import that stored many `kind=unknown` rows (unpadded day) needs
**re-init + re-import**. A second import after this fix would duplicate those
rows (idempotency includes `sent_at` + sender).

## `--locale`

Must be one of the five ids above. Do not add other languages in 0.1.0.

```bash
interlace import whatsapp ./chat.zip --locale tr-TR
```

## With vs without media

- `<Media omitted>` / locale equivalents → `attachments.omitted = 1`, no CAS blob.
- `IMG-… (file attached)` / `<attached: FILENAME>` → look up that zip entry, store
  in CAS (`cas/ab/cd/<blake3>`).
- Referenced name missing from the ZIP → `attachments.missing = 1` and a warning.
- Zip-slip paths (`../`, absolute, drive letters) are **rejected** per entry; other
  entries continue.

Binary media entries are capped at **512 MiB** each (D23). `_chat.txt` may be up
to `--max-bytes` (default **60 GiB**). Total CAS writes per import also stay under
`--max-bytes`. Entry count cap: 2 million.

## Identity keying (D16)

1. Strip WhatsApp’s leftover U+200E marks.
2. Locale `you_tokens` (`You` / `Siz` / `Du` / `Você` / …) → self identity,
   participant role `me`. On a DM-shaped 2-sender iOS chat, a sender whose
   folded name equals `init --name` (or a self identity display name) is also
   treated as you — see Groups vs DM.
3. Sender token that parses as a phone (E.164, using archive
   `default_phone_region` for national format) → `kind=phone`.
4. **DM only:** if the chat **title** (after stripping `WhatsApp Chat with ` /
   `WhatsApp Sohbeti: ` / …) parses as E.164, the counterpart is that **phone**
   even when per-line senders are a saved name. The saved name is stored as
   `display_name` on the same identity.
5. Otherwise `kind=display_name`. These **never** auto-merge.
6. **Never** insert `whatsapp_jid` from a ZIP. That kind is reserved for a future
   `msgstore` source.

`default_phone_region` is required at `interlace init` (D20). No silent country
default.

## Groups vs DM (D18)

`conversations.kind = group` if any of:

- (a) ≥ 2 distinct non-self, non-system senders, or
- (b) a group system template matches (created group / added / subject change), or
- (c) the locale lists an explicit group title prefix.

Else `kind = dm`. Person timelines hide groups unless `--include-groups`.

iOS 1:1 exports often name **both** sides with address-book names (no `You` /
`Siz`). That would trip (a). **Exception (D18-C):** if there are exactly two
human senders, one folded-equals your `init --name` (or a self identity
display name), the ZIP/title starts with a DM prefix (`WhatsApp Chat with `,
`WhatsApp Chat - `, `WhatsApp Sohbeti: `, …), and (b)/(c) did not fire →
`dm`. That sender is linked to the self person. A 2-person **group** with a
“created group” / added / subject line stays `group`. Peer names still never
auto-merge.

Two different chats that share a title collide on
`native_id = whatsapp:<folded_title>`. Pass `--conversation-name` to disambiguate.
iOS `_chat.txt` has no title in the filename; Interlace falls back to the ZIP
stem unless you pass `--conversation-name`.

## Resume

ZIP entries are DEFLATE. Interlace **never seeks inside a compressed entry**.

Resume re-reads `_chat.txt` from the start and skips lines with
`line_no <= checkpoint`. Cursor:

```json
{"entry": "_chat.txt", "line_no": 9000, "seq_bucket": "2020-01-01T10:15:00Z", "seq": 3}
```

```bash
interlace import whatsapp ./chat.zip --resume <run_id>
```

Interrupted runs (`SIGINT`, or `running` with heartbeat older than 15 minutes)
are safe to resume. Kill -9 leaves `status=running` until doctor/import notices.

## Ceiling warning

WhatsApp’s own export often stops around **~40 000** recent messages (less with
media). Interlace cannot recover older history from a ZIP. When an import hits
that many messages it records a warning and prints the earliest `sent_at`. This
is WhatsApp’s limit, not Interlace’s.

A first message that is a “you were added / created group” line sets
`conversations.extra_json.join_cutoff` so you know the export started mid-chat.

## Later export of the same chat

A later official export of the **same** chat (old lines plus newer ones)
**unions** into the existing conversation:

- only new rows insert
- overlapping messages keep the same `messages.id`
- you still have **one** conversation

Importing the **same ZIP twice** is unchanged: the `sources` row is reused, a
new `import_runs` row is recorded, and every message hits
`UNIQUE(idempotency_key)` and is counted as `skipped_dupes`.

Sameness is the folded chat title after stripping locale prefixes
(`WhatsApp Chat with `, `WhatsApp Sohbeti: `, …), or `--conversation-name` if
you passed it. That value is `native_id = whatsapp:<folded_title>`. Two ZIPs
that fold to different titles (or use different `--conversation-name`) are
different conversations. iOS `_chat.txt` has no title in the filename;
Interlace falls back to the ZIP stem unless you pass `--conversation-name`.

`<Media omitted>` later replaced by a real file is W9 / #60 (attachment
upgrade on the same `messages.id`), not this union.

## Limits

| Cap | Value |
| --- | --- |
| Attachment / binary zip entry | 512 MiB |
| `_chat.txt` uncompressed | `--max-bytes` (default 60 GiB) |
| Total CAS write per import | `--max-bytes` |
| Zip entries | 2 000 000 |
| No network | cargo-deny bans HTTP clients; this importer is file-only |

Same ZIP twice and a later overlapping export of the same chat: see
[Later export of the same chat](#later-export-of-the-same-chat).
