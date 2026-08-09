import { invoke } from "@tauri-apps/api/core";

export type Status = {
  path: string;
  owner_display_name?: string | null;
  default_phone_region?: string | null;
  messages: number;
  identities: number;
  persons_live: number;
  review_open: number;
  last_import?: { id: number; status: string } | null;
  warnings?: string[];
};

export type Person = {
  id: number;
  display_name: string;
  is_self: boolean;
};

export type Identity = {
  id: number;
  platform: string;
  kind: string;
  value: string;
  display_name?: string | null;
};

export type Attachment = {
  id: number;
  cas_hash?: string | null;
  filename?: string | null;
  mime?: string | null;
  kind: string;
  omitted: boolean;
  missing: boolean;
};

export type TimelineRow = {
  message_id: number;
  sent_at?: string | null;
  conversation_id: number;
  conversation_title?: string | null;
  conversation_kind: string;
  platform: string;
  from_me: boolean;
  subject?: string | null;
  body_text: string;
  attachments?: Attachment[];
};

export type LinkEvent = { id: number; ts: string; op: string };

export type SearchHit = {
  message_id: number;
  sent_at?: string | null;
  conversation_id: number;
  subject?: string | null;
  snippet: string;
  score: number;
  platform: string;
  conversation_kind: string;
  conversation_title?: string | null;
  person_id?: number | null;
  person_name?: string | null;
  attachments?: Attachment[];
};

export type ReviewRow = {
  id: number;
  score: number;
  reason: string;
  left_identity_id: number;
  right_person_id?: number | null;
  right_identity_id?: number | null;
  left_name: string;
  right_name?: string | null;
};

export type ReviewShow = {
  review: ReviewRow & { status: string };
  evidence: { type: string; score: number; detail: string }[];
  samples: { sent_at?: string | null; body_text: string }[];
};

export type ImportProgress = {
  status: "idle" | "running" | "done" | "failed" | string;
  path?: string | null;
  kind?: string | null;
  detail?: string | null;
  error?: string | null;
  stats?: {
    inserted_messages: number;
    skipped_dupes: number;
    warnings: number;
    rejected: number;
    inserted_identities: number;
    attachments_stored: number;
    review_enqueued: number;
    auto_person_merges: number;
  } | null;
};

export const api = {
  rememberedPath: () => invoke<string | null>("remembered_path"),
  pickFolder: () => invoke<string | null>("pick_folder"),
  init: (args: {
    path: string;
    phoneRegion: string;
    name: string | null;
    emails: string[];
    phones: string[];
  }) => invoke<Status>("init", args),
  open: (path: string) => invoke<Status>("open", { path }),
  status: () => invoke<Status>("status"),
  doctorIssues: () => invoke<string[]>("doctor_issues_cmd"),
  people: () => invoke<Person[]>("people"),
  personShow: (id: number) =>
    invoke<{ id: number; display_name: string; identities: Identity[] }>(
      "person_show",
      { id },
    ),
  personTimeline: (args: {
    id: number;
    includeGroups: boolean;
    limit?: number;
    before?: string | null;
  }) => invoke<TimelineRow[]>("person_timeline", args),
  merge: (a: number, b: number, keep: number) =>
    invoke<{ survivor: number; event_id: number }>("person_merge_cmd", {
      a,
      b,
      keep,
    }),
  unlink: (identityId: number) =>
    invoke<void>("person_unlink_cmd", { identityId }),
  undo: (eventId: number) => invoke<void>("person_undo_cmd", { eventId }),
  linkEvents: () => invoke<LinkEvent[]>("link_events"),
  pickImportPath: (folder: boolean) =>
    invoke<string | null>("pick_import_path", { folder }),
  search: (args: {
    q: string;
    personId?: number | null;
    from?: string | null;
    to?: string | null;
    platform?: string | null;
    includeGroups: boolean;
    limit?: number;
  }) => invoke<SearchHit[]>("search_cmd", { args }),
  searchBody: (messageId: number) => invoke<string>("search_body", { messageId }),
  reviewList: () => invoke<ReviewRow[]>("review_list_cmd"),
  reviewShow: (id: number) => invoke<ReviewShow>("review_show_cmd", { id }),
  reviewAccept: (id: number) => invoke<void>("review_accept_cmd", { id }),
  reviewReject: (id: number) => invoke<void>("review_reject_cmd", { id }),
  importStart: (args: { path: string; kind?: string | null; locale?: string | null }) =>
    invoke<void>("import_start", args),
  importProgress: () => invoke<ImportProgress>("import_progress"),
};
