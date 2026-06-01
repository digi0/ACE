import { useCallback, useSyncExternalStore } from "react";

// Single source of truth for the mobile breakpoint. The media queries in
// responsive.css use this same value as a literal (CSS @media cannot read a
// var()/JS value), so if you change it here, change it there too.
export const MOBILE_BREAKPOINT = 768;

/**
 * Returns true when the viewport is at or below the mobile breakpoint.
 *
 * Use this ONLY when the markup itself must differ between form factors
 * (e.g. <AppShell> rendering a bottom nav + drawer instead of the desktop
 * sidebar). Pure visual adaptation should still live in responsive.css —
 * keep the desktop/mobile split in CSS, not scattered through components.
 *
 * Implemented with useSyncExternalStore so it subscribes to matchMedia
 * without tearing or cascading renders, and is SSR-safe.
 */
export function useIsMobile(breakpoint = MOBILE_BREAKPOINT) {
  const query = `(max-width: ${breakpoint}px)`;

  const subscribe = useCallback(
    (callback) => {
      if (typeof window === "undefined") return () => {};
      const mql = window.matchMedia(query);
      mql.addEventListener("change", callback);
      return () => mql.removeEventListener("change", callback);
    },
    [query]
  );

  const getSnapshot = useCallback(
    () => typeof window !== "undefined" && window.matchMedia(query).matches,
    [query]
  );

  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}
