import { en, type ChromeKey } from "./locales/en";
import { tr } from "./locales/tr";

export type PackLang = "en" | "tr";

/** OS locale: first supported tag in preference order; `tr`/`tr-*` → tr, `en`/`en-*` → en; default en. */
export function detectLocale(): PackLang {
  const tags: string[] = [];
  if (typeof navigator !== "undefined") {
    if (Array.isArray(navigator.languages) && navigator.languages.length > 0) {
      tags.push(...navigator.languages);
    } else if (navigator.language) {
      tags.push(navigator.language);
    }
  }
  for (const raw of tags) {
    const tag = String(raw ?? "")
      .trim()
      .toLowerCase()
      .replaceAll("_", "-");
    if (tag === "tr" || tag.startsWith("tr")) {
      return "tr";
    }
    if (tag === "en" || tag.startsWith("en")) {
      return "en";
    }
  }
  return "en";
}

const locale: PackLang = detectLocale();
const pack = locale === "tr" ? tr : en;

/** Chrome lookup. Never pass body_text / snippet / display_name. */
export function t(key: ChromeKey): string {
  return pack[key] ?? en[key];
}
