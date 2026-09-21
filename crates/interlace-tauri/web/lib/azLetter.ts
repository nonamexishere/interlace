/** Display-letter for A–Z headings. Identity keying stays in fold.rs. */

const CF = /[\u200b\u200c\u200d\u200e\u200f\u2060\ufeff]/g;

const HONORIFICS = [
  "tr",
  "mr",
  "mrs",
  "ms",
  "dr",
  "prof",
  "sayın",
  "sn",
  "bey",
  "hanım",
  "hanim",
  "av",
  "mühendis",
  "muhendis",
];

function stripCf(s: string): string {
  return s.replace(CF, "");
}

function isAsciiPunctNotHyphen(c: string): boolean {
  if (c === "-") return false;
  const code = c.charCodeAt(0);
  return (
    (code >= 33 && code <= 47) ||
    (code >= 58 && code <= 64) ||
    (code >= 91 && code <= 96) ||
    (code >= 123 && code <= 126)
  );
}

function trimPunct(tok: string): string {
  let a = 0;
  let b = tok.length;
  while (a < b && isAsciiPunctNotHyphen(tok[a] ?? "")) a += 1;
  while (b > a && isAsciiPunctNotHyphen(tok[b - 1] ?? "")) b -= 1;
  return tok.slice(a, b);
}

function letterFrom(ch: string): string {
  if (ch === "i" || ch === "ı") return "I";
  return ch.toUpperCase();
}

/** First surviving token after İ→i, I→ı, strip Cf, lowercase, honorific drop.
 *  1-char tokens skip as prefixes (Dr Ada → A). A lone letter is that letter.
 *  Leading punctuation after strip Cf is `#` (do not skip punct to hunt a letter). */
export function azLetter(raw: string): string {
  const stripped = stripCf(raw);
  const lead = stripped.trimStart().charAt(0);
  if (lead && isAsciiPunctNotHyphen(lead)) return "#";
  const folded = stripped.replace("İ", "i").replace("I", "ı").toLowerCase();
  const long: string[] = [];
  const short: string[] = [];
  for (const part of folded.split(/\s+/)) {
    const tok = trimPunct(part);
    if (!tok) continue;
    if (HONORIFICS.includes(tok)) continue;
    if (tok.length < 2) {
      short.push(tok);
      continue;
    }
    long.push(tok);
  }
  const first = long[0] ?? short[0];
  if (first) return letterFrom(first.charAt(0));
  return "#";
}

/** Digits, then Turkish A–Z (i/ı already folded to I), then `#`. */
const LETTER_ORDER = "0123456789ABCÇDEFGĞHIJKLMNOÖPQRSŞTUÜVWXYZ";

export function letterRank(L: string): number {
  if (L === "#") return 1000;
  const i = LETTER_ORDER.indexOf(L);
  if (i >= 0) return i;
  return 500 + (L.codePointAt(0) ?? 0);
}

export function compareAzLetters(a: string, b: string): number {
  return letterRank(a) - letterRank(b);
}
