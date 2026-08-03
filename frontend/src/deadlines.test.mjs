/**
 * Self-check for the deadline picker.  Run:  node src/deadlines.test.mjs
 *
 * No framework by design — plain asserts, exits non-zero on failure. These are
 * the four ways the widget actually broke or nearly broke in practice.
 */
import assert from "node:assert/strict";
import { nextDeadlines, daysAway, fmtDate } from "./deadlines.js";

const NOW = new Date("2026-08-02T09:00:00");
const ev = (iso, event) => ({ iso_date: iso, event });

// Shaped like the real /calendar payload: one university-wide date repeated
// across every session of the term, plus session-specific noise.
const FEED = [
  { semester: "Summer 2026 - Maymester",            events: [ev("2026-08-03", "Declare Concurrent Majors")] },
  { semester: "Summer 2026 - First 6-Week Session", events: [ev("2026-08-03", "Declare Concurrent Majors")] },
  { semester: "Summer 2026 - Second 6-Week Session", events: [
      ev("2026-08-03", "Declare Concurrent Majors"),
      ev("2026-08-03", "Late Add - Deadline"),
  ]},
  { semester: "Summer 2026 - Regular Session", events: [
      ev("2026-08-03", "Declare Concurrent Majors"),
      ev("2026-07-01", "Classes Begin"),          // past — must be dropped
      ev("2026-08-12", "Withdrawal - Deadline"),
  ]},
  { semester: "Fall 2026 - Regular Session", events: [ev("2026-08-24", "Classes Begin")] },
];

// 1 · The same date published under four sessions collapses to one row.
const top = nextDeadlines(FEED, 4, NOW);
assert.equal(
  top.filter((e) => e.event === "Declare Concurrent Majors").length, 1,
  "duplicate university-wide dates must collapse to a single row",
);

// 2 · Regular Session wins, so 6-week add/drop noise never crowds the widget.
assert.ok(
  !top.some((e) => e.event === "Late Add - Deadline"),
  "session-specific noise must lose to the Regular Session",
);

// 3 · Past events are gone, and what's left is in date order.
assert.ok(!top.some((e) => e.iso_date === "2026-07-01"), "past events must be dropped");
assert.deepEqual(
  top.map((e) => e.iso_date),
  ["2026-08-03", "2026-08-12", "2026-08-24"],
  "results must be sorted ascending by date",
);

// 4 · Quarter systems (UCSD) name nothing "Regular Session" — fall back to
//     everything rather than render an empty widget.
const QUARTERS = [{ semester: "Fall Quarter 2026", events: [ev("2026-09-28", "Instruction Begins")] }];
assert.equal(nextDeadlines(QUARTERS, 4, NOW).length, 1, "must fall back when no Regular Session exists");

// 5 · Dates are parsed local, not UTC — the bug that shows "yesterday" to
//     everyone west of Greenwich.
assert.equal(daysAway("2026-08-02", NOW), 0, "today must be 0 days away");
assert.equal(daysAway("2026-08-03", NOW), 1, "tomorrow must be 1 day away");
assert.equal(fmtDate("2026-08-03"), "Aug 3");

// Degenerate inputs must not throw — the fetch can fail or return a stub.
assert.deepEqual(nextDeadlines(undefined, 4, NOW), []);
assert.deepEqual(nextDeadlines([], 4, NOW), []);

console.log("deadlines: all checks passed");
