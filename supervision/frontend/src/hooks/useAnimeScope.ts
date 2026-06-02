import { createScope, type Scope } from "animejs";
import { useEffect, type RefObject } from "react";

export function prefersReducedMotion() {
  if (typeof window === "undefined" || !window.matchMedia) {
    return false;
  }
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function useAnimeScope<T extends HTMLElement | SVGElement>(
  rootRef: RefObject<T>,
  setup: (scope?: Scope) => void | (() => void),
  dependencies: unknown[]
) {
  useEffect(() => {
    const root = rootRef.current;
    if (!root || prefersReducedMotion()) {
      return undefined;
    }

    const scope = createScope({ root }).add(setup);
    return () => scope.revert();
    // The caller owns the dependency list so animations can be intentionally replayed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);
}
