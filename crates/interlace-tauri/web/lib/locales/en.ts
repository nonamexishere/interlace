/** English UI chrome. Message bodies / names / snippets are not in this pack. */
export const en = {
  openArchive: "Open archive",
  openAnArchive: "Open an archive",
  openExisting: "Open existing…",
  createArchive: "Create archive…",
  doctor: "Doctor",
  people: "People",
  search: "Search",
  searchPlaceholder: "Search messages",
  review: "Review",
  import: "Import",
  accept: "Accept",
  reject: "Reject",
  noPeopleYet: "No people yet",
  selectAPerson: "Select a person",
  noDoctorIssues: "No doctor issues",
  nothingToReview: "Nothing to review",
  reviewEmptyBody:
    "Name-only WhatsApp matches show up here. They never auto-merge. Import Contacts if you expect a queue.",
  loadingReviewQueue: "Loading review queue…",
  linkThesePeople: "Link these people?",
  linkThesePeopleDesc: "Merge {n} people into one. Messages stay put.",
  stopSuggesting: "Stop suggesting this pair?",
  stopSuggestingDesc: "These people will not be suggested again.",
  undoLastLink: "Undo last link",
  undoLastLinkConfirm: "Undo last link?",
  undoLastLinkDesc:
    "Reverses the last identity graph change. Messages stay put.",
  undoing: "Undoing…",
  typeAQuery: "Type a query",
  noHits: "No hits",
  searchFilters: "Filters",
  searchFrom: "From",
  searchTo: "To",
  searchDateInvalid:
    "Check the date range. From and to must be valid dates, and from cannot be after to.",
  openingLastArchive: "Opening last archive",
  noFileSelected: "No file selected",
  importEmptyBody:
    "Pick a WhatsApp ZIP, Takeout folder, mbox, or contacts file. Folder picker only — no URLs.",
  pickFile: "Pick file",
  pickFileEllipsis: "Pick file…",
  cancel: "Cancel",
  backupUnit: "The folder is the backup unit.",
  notEncryptedAtRest: "Not encrypted at rest. FileVault is your encryption.",
  noSeparateBackup: "There is no separate backup command.",
  doNotKeepLive:
    "Do not keep the live archive in iCloud Drive, Dropbox, or Google Drive.",
  timeMachineOk:
    "Time Machine of the whole folder is fine after you close this window. See",
  cloudBanner:
    "This archive looks like it sits on iCloud, Dropbox, or Google Drive.",
  doctorPaneLead:
    "Same checks as interlace doctor. This window already holds the archive lock — close it before running doctor in a terminal.",
  doctorEmptyBody:
    "SQLite, FTS, and referenced CAS blobs look healthy. Unreferenced files still need GC CAS if you want them gone.",
  runIntegrityCheck: "Run integrity check?",
  runIntegrityCheckDesc:
    "Read-only PRAGMA integrity_check plus FTS integrity. Does not change messages.",
  integrityCheck: "Check",
  integrityCheckFinished: "Integrity check finished.",
  rebuildSearchIndex: "Rebuild search index?",
  rebuildSearchIndexDesc:
    "Recreates FTS triggers if missing and rebuilds the index. Messages and CAS stay put.",
  rebuild: "Rebuild",
  ftsRebuildFinished: "FTS rebuild finished.",
  gcUnusedCas: "Garbage-collect unused CAS files?",
  gcUnusedCasDesc:
    "Deletes blobs not referenced by attachments or contact photos. Cannot undo. Close other writers first.",
  deleteUnused: "Delete unused",
  casGcFinished: "CAS GC finished.",
  copyText: "Copy text",
  revealInFinder: "Reveal in Finder",
  collapseSidebar: "Collapse people sidebar",
  expandSidebar: "Expand people sidebar",
  inspector: "Inspector",
  identities: "Identities",
  lastActivity: "Last activity",
  findInThread: "Find in conversation",
  jumpToDay: "Jump to day",
} as const;

export type ChromeKey = keyof typeof en;
export type ChromePack = { [K in ChromeKey]: string };
