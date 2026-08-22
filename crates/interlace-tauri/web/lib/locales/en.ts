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
  typeAQuery: "Type a query",
  noHits: "No hits",
  searchFilters: "Filters",
  searchFrom: "From",
  searchTo: "To",
  searchDateInvalid:
    "Check the date range. From and to must be valid dates, and from cannot be after to.",
  openingLastArchive: "Opening last archive",
  backupUnit: "The folder is the backup unit.",
  notEncryptedAtRest: "Not encrypted at rest. FileVault is your encryption.",
  cloudBanner:
    "This archive looks like it sits on iCloud, Dropbox, or Google Drive.",
  doctorPaneLead:
    "Same checks as interlace doctor. This window already holds the archive lock — close it before running doctor in a terminal.",
  copyText: "Copy text",
  revealInFinder: "Reveal in Finder",
  collapseSidebar: "Collapse people sidebar",
  expandSidebar: "Expand people sidebar",
  inspector: "Inspector",
  identities: "Identities",
  lastActivity: "Last activity",
} as const;

export type ChromeKey = keyof typeof en;
export type ChromePack = { [K in ChromeKey]: string };
