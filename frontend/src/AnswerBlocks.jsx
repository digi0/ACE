/* Answer blocks — the rendered half of the visual policy.
 *
 * The backend decides whether a block is warranted, which kind, and ships its
 * data on the chat stream's done event. These draw it. Every component returns
 * null on missing data, so a block is never drawn empty.
 *
 * They sit OUTSIDE the message bubble, on the page's dotted surface — see
 * .msg-visual. A bubble is the shape of something said; these are things you
 * work with, and squeezing a planner spread into a speech bubble made it read
 * as a quotation of a plan rather than the plan.
 */

import { useCallback, useEffect, useRef, useState } from "react";

function Links({ links }) {
  if (!links?.length) return null;
  return (
    <span className="ab-links">
      {links.map((l) => (
        <a key={l.url} href={l.url} target="_blank" rel="noreferrer">{l.label}</a>
      ))}
    </span>
  );
}

/* ── cards: clubs, places, events, course slots ───────────────────────────────
 *
 * A carousel, not a grid. Six dining halls in an auto-fit grid inside a chat
 * column reflowed into a ragged two-and-a-half-column block whose last row was
 * half empty and whose cards were clipped — the width available here is neither
 * wide enough for a real grid nor stable enough to design one against. A rail
 * gives every card the same width whatever the column does, and makes the fact
 * that there are more of them off the right-hand edge legible instead of lost.
 *
 * Native scroll-snap does the work; the arrows are for mouse users, who cannot
 * swipe a trackpad. It is NOT wrapped in .ab — that class is the glass panel,
 * and a rail of cards is not a panel. Inheriting it was the original bug: the
 * grid got overflow:hidden and a gloss overlay from .ab while .ab-cards stripped
 * only the background and border, so the cards were clipped by a box that had
 * stopped looking like one.
 */
export function CardsBlock({ data }) {
  const rail = useRef(null);
  const [edge, setEdge] = useState({ left: false, right: false });

  const measure = useCallback(() => {
    const el = rail.current;
    if (!el) return;
    setEdge({
      left: el.scrollLeft > 4,
      right: el.scrollLeft + el.clientWidth < el.scrollWidth - 4,
    });
  }, []);

  useEffect(() => {
    measure();
    const el = rail.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [measure, data]);

  if (!data?.items?.length) return null;
  const { kind, items, hours_url } = data;

  const step = (dir) => {
    const el = rail.current;
    if (!el) return;
    const card = el.querySelector(".ab-card");
    const by = card ? card.offsetWidth + 10 : el.clientWidth * 0.8;
    el.scrollBy({ left: dir * by, behavior: "smooth" });
  };

  return (
    <div className={`ab-carousel ab-carousel--${kind}`}>
      <div className={`ab-rail-wrap${edge.left ? " fade-l" : ""}${edge.right ? " fade-r" : ""}`}>
        <div className="ab-cards" ref={rail} onScroll={measure}
             tabIndex={0} role="group" aria-label={`${items.length} ${kind}`}>
          {items.map((it, i) => (
            <div className={`ab-card${it.state === "blocked" ? " is-blocked" : ""}`} key={i}>
              <div className="ab-card-main">
                <span className="ab-card-title">{it.title}</span>
                {it.subtitle && <span className="ab-card-sub">{it.subtitle}</span>}
                {it.meta && <span className="ab-card-meta">{it.meta}</span>}
                {it.body && <span className="ab-card-body">{it.body}</span>}
                {it.note && <span className="ab-card-note">{it.note}</span>}
                <Links links={it.links} />
              </div>
              {it.value != null && (
                <span className="ab-card-value">{it.value}<i>{it.unit}</i></span>
              )}
            </div>
          ))}
        </div>
        {edge.left && (
          <button className="ab-nav ab-nav--l" onClick={() => step(-1)}
                  aria-label="Previous">‹</button>
        )}
        {edge.right && (
          <button className="ab-nav ab-nav--r" onClick={() => step(1)}
                  aria-label="Next">›</button>
        )}
      </div>
      <div className="ab-carousel-foot">
        <span className="ab-rail-meta">{items.length} {kind}</span>
        {hours_url && (
          <a className="ab-foot-link" href={hours_url} target="_blank" rel="noreferrer">
            live hours →
          </a>
        )}
      </div>
    </div>
  );
}

/* ── checklist: a procedure you can tick off ─────────────────────────────────
 *
 * It called itself a checklist and had painted-on boxes. A retroactive
 * withdrawal is filed over days, across offices, and the whole value of writing
 * it as steps is knowing which one you are on when you come back to it — so the
 * ticks persist, keyed by the procedure rather than by the message, and a
 * student who asks the same question twice finds their progress where they left
 * it. localStorage is right for this: it is one person's place in a form, not
 * a record ACE should be holding on a server.
 */
function useTicks(key, count) {
  const store = `ace_steps_${key}`;
  const [done, setDone] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(store) || "[]");
      return new Set(saved.filter((i) => i < count));
    } catch { return new Set(); }
  });
  const toggle = (i) => setDone((prev) => {
    const next = new Set(prev);
    next.has(i) ? next.delete(i) : next.add(i);
    try { localStorage.setItem(store, JSON.stringify([...next])); } catch { /* full or blocked */ }
    return next;
  });
  return [done, toggle];
}

export function ChecklistBlock({ data }) {
  const steps = data?.steps || [];
  const key = (data?.title || "steps").toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const [done, toggle] = useTicks(key, steps.length);
  if (!steps.length) return null;

  return (
    <div className="ab ab-sheet">
      <div className="ab-rail">
        <span className="ab-tab">{data.title?.slice(0, 28) || "steps"}</span>
        <span className="ab-rail-meta">
          {done.size}/{steps.length} done
        </span>
        {done.size > 0 && done.size === steps.length && (
          <span className="ab-rail-done">all clear</span>
        )}
      </div>
      <div className="ab-sheet-body">
        <ol className="ab-steps">
          {steps.map((s, i) => (
            <li key={i} className={done.has(i) ? "is-done" : ""}>
              <button type="button" className="ab-box" onClick={() => toggle(i)}
                      aria-pressed={done.has(i)} aria-label={`Step ${i + 1}: ${s}`} />
              <span className="ab-step-text">{s}</span>
            </li>
          ))}
        </ol>
        {data.facts?.length > 0 && (
          <aside className="ab-facts">
            {data.facts.map((f) => (
              <div key={f.k}><span className="ab-k">{f.k}</span><b>{f.v}</b></div>
            ))}
            {data.source && (
              <a className="ab-foot-link" href={data.source} target="_blank" rel="noreferrer">
                source →
              </a>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}

/* ── strip: the term at a glance ────────────────────────────────────────── */
export function StripBlock({ data }) {
  if (!data?.events?.length) return null;
  return (
    <div className="ab ab-strip">
      <div className="ab-rail">
        <span className="ab-tab">{data.term || "this term"}</span>
      </div>
      <ol className="ab-timeline">
        {data.events.map((e, i) => (
          <li className={e.hot ? "is-next" : ""} key={i}>
            <span className="ab-dot" aria-hidden />
            <span className="ab-tl-label">{e.label}</span>
            <span className="ab-tl-date">{e.date}</span>
            {e.days != null && e.days >= 0 && (
              <span className="ab-tl-days">{e.days === 0 ? "today" : `${e.days}d`}</span>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

/* ── plan: the planner spread ───────────────────────────────────────────── */
export function PlanBlock({ data }) {
  if (!data?.terms?.length) return null;
  const pct = data.progress?.total
    ? Math.min(100, Math.round((data.progress.done / data.progress.total) * 100))
    : null;
  return (
    <div className="ab ab-plan">
      <div className="ab-rail">
        <span className="ab-tab">plan</span>
        {data.progress && (
          <span className="ab-rail-meta">{data.progress.done}/{data.progress.total}</span>
        )}
        {!data.personalised && <span className="ab-rail-meta">no audit</span>}
      </div>
      <div className="ab-plan-cols">
        {data.terms.map((t) => (
          <section className="ab-term" key={t.label}>
            <header><h4>{t.label}</h4></header>
            <ul>
              {t.courses.map((c) => (
                <li className={c.blocked ? "is-blocked" : ""} key={c.code}>
                  <i className="ab-box" aria-hidden />
                  <span className="ab-c">{c.code}</span>
                  <span className="ab-n">{c.credits ?? ""}</span>
                </li>
              ))}
            </ul>
            <footer><span>total</span><b>{t.total}</b></footer>
          </section>
        ))}
      </div>
      {pct != null && (
        <div className="ab-progress" title={`${data.progress.done} of ${data.progress.total} credits`}>
          <i style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  );
}
