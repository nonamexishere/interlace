export const SANDBOX_DENIED =
  "macOS blocked that folder. Use Open existing\u2026 once so Interlace can remember it.";

export function friendly(raw: string) {
  if (raw === SANDBOX_DENIED || raw.includes(SANDBOX_DENIED)) return SANDBOX_DENIED;
  if (raw.includes("archive in use")) {
    return `Archive is locked by another Interlace window or CLI writer. Close that process and try again.\n${raw}`;
  }
  if (raw.includes("pass --locale") || raw.includes("locale vote")) {
    return `Could not guess the WhatsApp language pack. Set Locale (for example tr-TR) on the Import tab and retry.\n${raw}`;
  }
  if (raw.includes("not an Interlace archive")) {
    return `That folder is not an archive (no INTERLACE.toml). Create one or open your existing archive folder.\n${raw}`;
  }
  if (raw.includes("no archive open")) {
    return "No archive is open. An import may still be running — wait for it, or open a folder.";
  }
  return raw;
}

/** Tauri file-drop paths only — reject http(s) and other URL schemes. */
export function isDroppedUrl(path: string): boolean {
  const s = path.trim();
  if (s.startsWith("http://") || s.startsWith("https://")) return true;
  return /^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//.test(s);
}
