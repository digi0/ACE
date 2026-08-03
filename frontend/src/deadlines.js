/**
 * Deadline selection for the widget rail. Pure functions, no JSX — kept in its
 * own module so `node src/deadlines.test.mjs` can exercise it without a build
 * step or a test framework.
 */

const MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function fmtDate(iso) {
  const [, mm, dd] = iso.split("-").map(Number);
  return `${MONTHS[mm]} ${dd}`;
}

/**
 * Whole days from local midnight today. The `T00:00:00` matters: without it the
 * string parses as UTC, and every date reads one day early for anyone west of
 * Greenwich — which is all of Penn State and all of UCSD.
 */
export function daysAway(iso, now = new Date()) {
  const today = new Date(now);
  today.setHours(0, 0, 0, 0);
  return Math.round((new Date(iso + "T00:00:00") - today) / 86400000);
}

/**
 * The soonest `limit` deadlines a student plausibly cares about.
 *
 * Two passes are needed on the raw feed:
 *
 *  1. DEDUPE. Penn State publishes the same university-wide date under every
 *     session of a term, so "Declare Concurrent Majors" arrives four times for
 *     one 3 Aug deadline and fills the whole widget with a single event.
 *
 *  2. PREFER THE REGULAR SESSION. 163 upcoming events collapse to 119 after
 *     dedupe, but the nearest ones are still 6-week-session add/drop dates that
 *     almost nobody is enrolled in. Restricting to the Regular Session leaves 65
 *     and puts real dates on top. We have no enrollment data, so this is a
 *     heuristic, not a fact — hence the fallback: if no semester is named that
 *     way (UCSD's quarters won't be), use everything rather than show nothing.
 */
export function nextDeadlines(semesters, limit = 4, now = new Date()) {
  const all = Array.isArray(semesters) ? semesters : Object.values(semesters ?? {});
  const regular = all.filter((s) => /regular session/i.test(s?.semester ?? ""));
  const source = regular.length ? regular : all;

  const seen = new Set();
  return source
    .flatMap((s) => s?.events ?? [])
    .filter((e) => e?.iso_date && daysAway(e.iso_date, now) >= 0)
    .sort((a, b) => a.iso_date.localeCompare(b.iso_date))
    .filter((e) => {
      const key = `${e.iso_date}|${e.event}`;
      return seen.has(key) ? false : (seen.add(key), true);
    })
    .slice(0, limit);
}
