/* Prerequisite map — drawn, not listed, and walkable.
 *
 * The rule is "(CMPSC 122 or CMPSC 132) AND (CMPSC 360 or MATH 311W)". A list of
 * chips cannot show that: you cannot see which options belong to the same slot,
 * or that the two slots are joined by AND, or that satisfying one option in a
 * group is enough. Groups on the left, curved wires converging on the course in
 * question, what it opens on the right — the shape carries the logic.
 *
 * Three states per node, because two is not enough: passed, in progress this
 * term (the state that answers "can I take this NEXT fall?"), and not taken.
 *
 * Clicking any node re-centres the map on that course. The real question is
 * never one course deep — "can I take 465?" becomes "…so what does 360 need?" —
 * and answering that by typing another chat message spends a model call on a
 * lookup that is local. /prereq-graph does it in one request.
 *
 * Nodes are positioned by transform on a <g>, not by x/y on the rect, so the
 * re-centre TWEENS: the courses that appear in both graphs slide to their new
 * places instead of the whole picture blinking. That continuity is the point —
 * it is what makes it read as one graph you are moving through rather than a
 * series of unrelated pictures.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "./api";

const W = 720;
const COL = { group: 12, gw: 196, target: 300, tw: 176, unlock: 536, uw: 172 };

function layout(groups, unlocks) {
  const rowH = 34, groupGap = 16, headH = 15;
  let y = 8;
  const laid = groups.map((g) => {
    const top = y;
    y += headH;
    const nodes = g.map((n) => {
      const node = { ...n, y, h: rowH - 6 };
      y += rowH;
      return node;
    });
    y += groupGap;
    return { top, nodes, mid: (top + headH + y - groupGap) / 2 };
  });
  const leftH = Math.max(y, 60);
  const uH = 30;
  const unlocksTop = Math.max(8, leftH / 2 - (unlocks.length * uH) / 2);
  const laidUnlocks = unlocks.map((u, i) => ({ ...u, y: unlocksTop + i * uH }));
  const height = Math.max(leftH, unlocksTop + unlocks.length * uH) + 10;
  return { laid, laidUnlocks, height, midY: leftH / 2 };
}

function stateOf(n) {
  if (n.done) return "done";
  if (n.in_progress) return "doing";
  return "todo";
}

function Node({ code, title, x, y, w, h, cls, onOpen, mark, credits, sub }) {
  const clickable = Boolean(onOpen);
  return (
    <g
      className={`pm-node ${cls}${clickable ? " is-clickable" : ""}`}
      transform={`translate(${x} ${y})`}
      onClick={clickable ? onOpen : undefined}
      onKeyDown={clickable ? (e) => (e.key === "Enter" || e.key === " ") && onOpen(e) : undefined}
      tabIndex={clickable ? 0 : undefined}
      role={clickable ? "button" : undefined}
      aria-label={clickable ? `Re-centre the map on ${code}` : code}
    >
      <rect width={w} height={h} rx="3" />
      <text className="pm-code" x="11" y={sub ? 13 : h / 2 + 4}>{code}</text>
      {sub && <text className="pm-sub" x="11" y="24">{sub}</text>}
      {credits && <text className="pm-cr" x={w - 13} y="21">{credits} cr</text>}
      {mark && <text className={`pm-mark ${mark.cls}`} x={w - 12} y={h / 2 + 4}>{mark.glyph}</text>}
      {title && <title>{title}</title>}
    </g>
  );
}

export default function PrereqMapBlock({ data }) {
  const [graph, setGraph] = useState(data);
  const [trail, setTrail] = useState([]);
  const [loading, setLoading] = useState(null);
  const live = useRef(true);

  useEffect(() => { setGraph(data); setTrail([]); }, [data]);
  useEffect(() => () => { live.current = false; }, []);

  const open = useCallback(async (code, { back = false } = {}) => {
    if (!code || code === graph?.target?.code) return;
    setLoading(code);
    try {
      const next = await apiFetch(`/prereq-graph/${encodeURIComponent(code)}`);
      if (!live.current || !next?.target) return;
      setTrail((t) => (back ? t.slice(0, -1) : [...t, graph.target.code]));
      setGraph(next);
    } catch {
      // A course with no record in programs.json simply is not walkable. The
      // map it already shows stays correct, so failing silently is honest here.
    } finally {
      if (live.current) setLoading(null);
    }
  }, [graph]);

  if (!graph?.target) return null;
  const { target, groups = [], unlocks = [], unlocks_more = 0,
          eligible, on_track, has_record } = graph;

  const shown = unlocks.slice(0, 4);
  const rest = unlocks.length - shown.length + (unlocks_more || 0);
  const { laid, laidUnlocks, height, midY } = layout(groups, shown);
  const tY = midY - 26;

  const verdict = !has_record ? null
    : eligible ? { label: "eligible now", tone: "ok" }
    : on_track ? { label: "on track — finish what's in progress", tone: "ok" }
    : { label: "not yet eligible", tone: "" };

  const clip = (s, n) => (s || "").length > n ? s.slice(0, n - 1) + "…" : (s || "");

  return (
    <figure className={`pm${loading ? " is-loading" : ""}`}
            aria-label={`Prerequisite map for ${target.code}`}>
      <figcaption className="pm-head">
        <span className="pm-label">prerequisite map</span>
        {verdict && <span className={`pm-verdict ${verdict.tone}`}>{verdict.label}</span>}
        {trail.length > 0 && (
          <button className="pm-back" onClick={() => open(trail[trail.length - 1], { back: true })}>
            ← {trail[trail.length - 1]}
          </button>
        )}
      </figcaption>

      <svg className="pm-svg" viewBox={`0 0 ${W} ${height}`} role="img">
        {/* wires: every group feeds the target */}
        {laid.map((g, i) => (
          <path key={`w${i}`} className="pm-wire"
                d={`M ${COL.group + COL.gw} ${g.mid} C ${COL.group + COL.gw + 46} ${g.mid},
                    ${COL.target - 46} ${tY + 26}, ${COL.target} ${tY + 26}`} />
        ))}
        {laid.length > 1 && (
          <text className="pm-join" x={COL.target - 52} y={tY + 22}>AND</text>
        )}
        {/* wires: target opens these */}
        {laidUnlocks.map((u, i) => (
          <path key={`u${i}`} className="pm-wire"
                d={`M ${COL.target + COL.tw} ${tY + 26} C ${COL.target + COL.tw + 40} ${tY + 26},
                    ${COL.unlock - 40} ${u.y + 11}, ${COL.unlock} ${u.y + 11}`} />
        ))}

        {/* groups */}
        {laid.map((g, i) => (
          <g key={`g${i}`}>
            <text className="pm-grouplabel" x={COL.group} y={g.top + 10}>
              {groups.length > 1 ? `group ${i + 1} — one of` : "requires"}
            </text>
            {/* Keyed by CODE, not by index, so React moves the same node rather
                than rebuilding it — which is what lets the tween happen. */}
            {g.nodes.map((n) => (
              <Node key={n.code} code={n.code} title={n.title}
                    sub={n.title ? clip(n.title, 30) : ""}
                    x={COL.group} y={n.y} w={COL.gw} h={n.h}
                    cls={`is-${stateOf(n)}`} onOpen={() => open(n.code)}
                    mark={n.done ? { glyph: "✓", cls: "" }
                        : n.in_progress ? { glyph: "◐", cls: "now" } : null} />
            ))}
          </g>
        ))}

        {/* the course asked about */}
        <Node key={target.code} code={target.code} title={target.title}
              sub={clip(target.title, 26)} x={COL.target} y={tY}
              w={COL.tw} h={52} cls="is-target" credits={target.credits} />

        {/* what it opens */}
        {shown.length > 0 && (
          <text className="pm-grouplabel" x={COL.unlock} y={laidUnlocks[0].y - 7}>opens</text>
        )}
        {laidUnlocks.map((u) => (
          <Node key={u.code} code={u.code} title={u.title} x={COL.unlock} y={u.y}
                w={COL.uw} h={22} cls="is-next" onOpen={() => open(u.code)} />
        ))}
        {rest > 0 && laidUnlocks.length > 0 && (
          <text className="pm-more" x={COL.unlock}
                y={laidUnlocks[laidUnlocks.length - 1].y + 36}>+{rest} more</text>
        )}
      </svg>

      <div className="pm-legend">
        <span><i className="k done" />passed</span>
        <span><i className="k doing" />in progress</span>
        <span><i className="k todo" />not taken</span>
        <span><i className="k target" />asked about</span>
        <span className="pm-hint">click any course to follow it</span>
      </div>
    </figure>
  );
}
