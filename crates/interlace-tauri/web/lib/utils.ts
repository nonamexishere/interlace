import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Person } from "./api";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Same rules as `interlace_core::people::merge_targets`. In-memory — no IPC. */
export function mergeTargets(
  people: Person[],
  selectedId: number,
  allowSelf: boolean,
  query: string,
): Person[] {
  const q = query.trim().toLowerCase();
  return people.filter((p) => {
    if (p.id === selectedId) return false;
    if (!allowSelf && p.is_self) return false;
    if (q && !p.display_name.toLowerCase().includes(q)) return false;
    return true;
  });
}
