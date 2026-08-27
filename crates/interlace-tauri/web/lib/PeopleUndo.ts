import type { LinkEvent, Person } from "./api";

export const UNDOABLE = new Set(["merge_persons", "link", "unlink"]);

export function undoableFrom(events: LinkEvent[]): LinkEvent[] {
  const undone = new Set(
    events
      .filter((e) => e.op === "split_person" && e.undo_of != null)
      .map((e) => e.undo_of as number),
  );
  return events.filter(
    (e) => UNDOABLE.has(e.op) && e.actor === "user" && !undone.has(e.id),
  );
}

export function undoOpLabel(op: string) {
  if (op === "merge_persons") return "Merge";
  if (op === "link") return "Link";
  if (op === "unlink") return "Unlink";
  return op;
}

export function undoPersonName(e: LinkEvent, people: Person[]) {
  if (e.loser_display_name) return e.loser_display_name;
  const ids = [e.person_id, e.keep, e.loser].filter((id): id is number => id != null);
  for (const id of ids) {
    const p = people.find((x) => x.id === id);
    if (p) return p.display_name;
  }
  return undefined;
}

export function undoRowLabel(e: LinkEvent, people: Person[]) {
  const op = undoOpLabel(e.op);
  const name = undoPersonName(e, people);
  return name ? `${op} ${name}` : op;
}

export function personLabel(p: { display_name: string; is_self: boolean }) {
  return p.is_self ? `${p.display_name} (self)` : p.display_name;
}

export function personById(people: Person[], id: number | null): Person | undefined {
  if (id == null) return undefined;
  return people.find((p) => p.id === id);
}

export function nearestVisibleTlIndex(from: number, visible: number[]): number {
  if (!visible.length) return from;
  let best = visible[0];
  let bestDist = Math.abs(visible[0] - from);
  for (let i = 1; i < visible.length; i++) {
    const idx = visible[i];
    const d = Math.abs(idx - from);
    if (d < bestDist || (d === bestDist && idx > best)) {
      best = idx;
      bestDist = d;
    }
  }
  return best;
}
