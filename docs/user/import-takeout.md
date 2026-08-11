# Import Takeout / Gmail / Contacts

Interlace reads **Google Takeout** dumps and standalone Gmail mbox / Contacts
files. Nothing is uploaded.

## Preferred path (extract to `Takeout/` dir)

1. Download Takeout (Mail + Contacts).
2. Extract every zip into **one** merged `Takeout/` tree.
3. Import that directory:

```bash
interlace import takeout ~/Downloads/Takeout
```

This is the documented happy path. You can also pass a single Takeout zip, a
standalone `.mbox`, `.vcf`, or Google/Outlook `.csv`.

## Contacts

vCard 2.1/3.0 as Takeout emits: `FN`, `N`, `TEL`, `EMAIL`, `UID`, `ORG`, `PHOTO`
(base64). Folded lines are unfolded.

`persist_contact` creates **one person per card** and links that card’s own
phones/emails with `link_reason=takeout_vcard`. It does **not** merge across
cards. **`resolve_run`** (after the import commits) is the only place that
auto-links exact phone/email and auto person-merges.

UID-less cards get `uid = syn:` + blake3 of FN + sorted channels. Re-import of
the same file hits `UNIQUE (source_id, uid)` and does not create a second person.

PHOTO bytes may go into CAS for display. `photo_dhash` is **not** computed in
Phase 1 (D14).

Contacts is the identity bridge between WhatsApp phones and Gmail addresses.

## Gmail mbox

mboxrd: record starts at byte 0 or a newline then `From ` (space, no colon)
at column 0. Takeout All-mail uses that shape — no blank line is required
between records. `\r\nFrom ` is also a record start. Body lines `>From `
are not separators; they lose one leading `>` when the body is read.

| Header | Use |
| --- | --- |
| `Message-ID` | idempotency `gmail:<lowercase id>` |
| *(missing)* | `gmail-hash:` + blake3 of unescaped rfc822 |
| `X-GM-THRID` | conversation `gmail-thrid:<id>` |
| `X-Gmail-Labels` | labels; **Duplicate Message-ID unions labels** |
| `From` `To` `Cc` `Bcc` | identities + recipients |
| `Subject` `Date` | subject / `sent_at` (else mbox From_ date) |

`--preserve-raw` is **Phase 2, default off**. Phase 1 stores decoded text +
attachments only.

## Multi-zip probe (Spike 4)

Supported:

1. Extracted `Takeout/` directory.
2. One or more **independent** `.zip` files whose `Takeout/**` paths are
   **disjoint** (e.g. mail in zip 1, contacts in zip 2).

**Fatal** (never silent):

- Sibling `*.z01` / `*.z02` (PKWare spanned zip). Extract, then pass the dir.
- The same logical `Takeout/...` path in more than one zip — including split
  mbox fragments with the same basename. Extract and merge directories, then
  import the tree. Interlace does **not** concatenate same-path mbox fragments.

## Spill files

A Takeout **mbox inside a zip** is spilled to
`$ARCHIVE/imports/<run_id>/spill/<basename>.mbox` (D22 — no seek inside DEFLATE),
then read from that file. Spill is deleted when the run status becomes `done`.

Standalone `.mbox` is read in place with a byte-offset checkpoint.

## Labels union

The same Message-ID appearing under two Gmail labels is one message.
`PersistOutcome::Duplicate` still calls `persist_labels` so the label set is the
union. That is the only non-insert-only mail metadata write.

## `--preserve-raw`

Not in Phase 1. When it lands (Phase 2) it will CAS the original rfc822; default
stays **off**.

At the end of every Takeout import Interlace records a **non-blocking warning**:
deleting the Takeout dump loses bit-perfect raw rfc822. There is no yes/no
confirm (OQ5).

## Limits

Same D23 caps as WhatsApp: 512 MiB per decoded MIME attachment; mbox/vcf/csv
uncompressed ≤ `--max-bytes` (default 60 GiB); 2 M zip entries.
