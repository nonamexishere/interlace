import { en, type ChromeKey } from "./locales/en";
import { tr } from "./locales/tr";

export type PackLang = "en" | "tr";

/** OS locale: `tr` / `tr-*` → tr pack; everything else → en. */
export function detectLocale(): PackLang {
  const tags: string[] = [];
  if (typeof navigator !== "undefined") {
    if (Array.isArray(navigator.languages)) {
      tags.push(...navigator.languages);
    }
    if (navigator.language) {
      tags.push(navigator.language);
    }
  }
  for (const raw of tags) {
    const tag = String(raw ?? "")
      .trim()
      .toLowerCase()
      .replaceAll("_", "-");
    if (tag === "tr" || tag.startsWith("tr-")) {
      return "tr";
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
