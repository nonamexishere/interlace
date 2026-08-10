# People, review queue, and undo

Interlace never stores a message as “belonging to a person.” The chain is
always **Message → Identity → Person**. Merges move identity links; they do
not rewrite `messages.sender_identity_id`.

## Auto-merge rule

Automation is an assistant. The **only** auto actions are exact identifier
matches:

| Identifier | Normalized form | Auto? |
| --- | --- | --- |
| Phone | E.164 (`+` and country code, no spaces) | yes, 0.99 |
| Email | lowercase; **Gmail/googlemail** fold (D25) | yes, 0.99 |
| Display name / username | `name_fold` | **never** auto |

`default_phone_region` (ISO 3166-1 alpha-2) is **required at `interlace init`**.
There is no silent default (D20). National numbers that cannot be parsed are
left un-normalized and **do not** auto-merge.

**Gmail fold (D25):** for `gmail.com` / `googlemail.com` only: map
`googlemail.com` → `gmail.com`, drop `+tag`, delete `.` from the local part.
So `a.b+x@gmail.com` ≡ `ab@googlemail.com` ≡ `ab@gmail.com`.
Non-Gmail domains stay exact: `a+x@corp.com` ≠ `a@corp.com`.

Import order does not matter (D15). WhatsApp-then-Contacts and Contacts-then-WhatsApp
end as one live person for the same E.164/email (I5).

Name-only WhatsApp senders (`kind=display_name`) **never auto-merge** onto a
Contacts/phone/email person (I2). After that review row is enqueued (when a
similar live person already exists), each leftover name gets its **own**
person so a WA-first archive has a people list. A name that fold-equals a
group conversation title is not promoted. Two contact cards that share a
phone but have incompatible names block auto-link and enqueue review (I3).

`persist_contact` creates one person per vCard (`takeout_vcard`) and does **not**
merge across cards. **`resolve_run`** (after every import) is the only place
that auto-links and auto person-merges.

## Review queue

```
interlace review list
interlace review show <id>
interlace review accept <id>
interlace review reject <id>
```

`review show` prints both display names, identifiers, each evidence line, and a
few sample messages. Accept links the left identity with
`link_reason=review_accepted`. Reject suppresses that pair for this archive
(the matcher skips `rejected` rows).

Name similarity scores 0.40–0.70 go to review. Nothing name-based auto-merges.
A suggestion needs a **strong token** (same given name or surname, or a
one-letter typo on a 4+ letter token). Two unrelated two-word names are not
similar just because Jaro–Winkler on the whole string is 0.41.

## Undo

```
interlace person merge A B [--keep ID]
interlace person unlink IDENTITY
interlace person undo EVENT
```

`person merge` survivors default to `min(A,B)` unless `--keep`. The loser is
tombstoned (`merged_into` set); all `person_identities` rows move. **Zero
`messages` rows are touched.**

`person undo <event_id>` inverts `identity_link_events.payload_json` (revive
loser, move identities back). **I4:** every `messages.sender_identity_id` is
bitwise unchanged.

`person unlink` drops the `person_identities` row only. The identity and its
messages remain.

## Self person

The desktop app (UI3) shows the same person list and D18 timeline (groups
hidden until toggled). Merge / unlink / undo in the window call the same
core functions as the CLI.

`interlace init` creates `persons.is_self=1` even with zero emails/phones, plus
owner identities for the addresses you typed. WhatsApp `You` / `Siz` / `Du` /
`Você` tokens are locale-pack self senders, not automatically the owner person
until you link them. **Exception:** on a DM-shaped 2-sender iOS chat, a sender
matching `init --name` (exact name fold) is linked to the self person
(`self_declared` / system). See `docs/user/import-whatsapp.md`.
