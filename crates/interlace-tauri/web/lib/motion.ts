import { MediaQuery } from "svelte/reactivity";

/** OS `prefers-reduced-motion: reduce`. CSS 0.01ms is not enough for Svelte JS transitions. */
export const prefersReducedMotion = new MediaQuery("prefers-reduced-motion: reduce");

/** Chrome fade / fly / slide: 150–250ms, or 0 when reduced. */
export function chromeMotionMs(ms = 180): number {
  return prefersReducedMotion.current ? 0 : ms;
}
