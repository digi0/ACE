/* Answer blocks — the rendered half of the visual policy.
 *
 * The backend decides whether a block is warranted, which kind, and ships its
 * data on the chat stream's done event. These draw it. Every component returns
 * null on missing data, so a block is never drawn empty.
 *
 * Shapes follow the demos: contained inside the bubble rather than full-bleed,
 * a planner's ruled rows and running totals, and the accent used once per block
 * — on the thing the answer is about.
 */

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

/* ── cards: clubs, places, events, course slots ─────────────────────────── */
export function CardsBlock({ data }) {
  if (!data?.items?.length) return null;
  const { kind, items, hours_url } = data;
  return (
    <div className={`ab ab-cards ab-cards--${kind}`}>
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
      {hours_url && (
        <a className="ab-foot-link" href={hours_url} target="_blank" rel="noreferrer">
          live hours →
        </a>
      )}
    </div>
  );
}

/* ── checklist: a procedure you can tick off ────────────────────────────── */
export function ChecklistBlock({ data }) {
  if (!data?.steps?.length) return null;
  return (
    <div className="ab ab-sheet">
      <div className="ab-rail">
        <span className="ab-tab">{data.title?.slice(0, 28) || "steps"}</span>
        <span className="ab-rail-meta">{data.steps.length} steps</span>
      </div>
      <div className="ab-sheet-body">
        <ol className="ab-steps">
          {data.steps.map((s, i) => (
            <li key={i}><i className="ab-box" aria-hidden />{s}</li>
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
