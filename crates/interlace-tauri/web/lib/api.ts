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
};

export type LinkEvent = { id: number; ts: string; op: string };

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
};
