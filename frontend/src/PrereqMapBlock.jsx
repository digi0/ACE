/* Prerequisite map — drawn, not listed.
 *
 * The rule is "(CMPSC 122 or CMPSC 132) AND (CMPSC 360 or MATH 311W)". A list of
 * chips cannot show that: you cannot see which options belong to the same slot,
 * or that the two slots are joined by AND, or that satisfying one option in a
 * group is enough. Groups on the left, curved wires converging on the course in
 * question, what it opens on the right — the shape carries the logic.
 *
 * Three states per node, because two is not enough: passed, in progress this
 * term (the state that answers "can I take this NEXT fall?"), and not taken.
 */

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

export default function PrereqMapBlock({ data }) {
  if (!data?.target) return null;
  const { target, groups = [], unlocks = [], unlocks_more = 0,
          eligible, on_track, has_record } = data;

  const shown = unlocks.slice(0, 4);
  const rest = unlocks.length - shown.length + (unlocks_more || 0);
  const { laid, laidUnlocks, height, midY } = layout(groups, shown);
  const tY = midY - 26;

  const verdict = !has_record ? null
    : eligible ? { label: "eligible now", tone: "ok" }
    : on_track ? { label: "on track — finish what's in progress", tone: "ok" }
    : { label: "not yet eligible", tone: "" };

  return (
    <figure className="pm" aria-label={`Prerequisite map for ${target.code}`}>
      <figcaption className="pm-head">
        <span className="pm-label">prerequisite map</span>
        {verdict && <span className={`pm-verdict ${verdict.tone}`}>{verdict.label}</span>}
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
            {g.nodes.map((n) => (
              <g key={n.code} className={`pm-node is-${stateOf(n)}`}>
                <rect x={COL.group} y={n.y} width={COL.gw} height={n.h} rx="3" />
                <text className="pm-code" x={COL.group + 11} y={n.y + (n.title ? 13 : 18)}>
                  {n.code}
                </text>
                {n.title && (
                  <text className="pm-sub" x={COL.group + 11} y={n.y + 24}>
                    {n.title.length > 30 ? n.title.slice(0, 29) + "…" : n.title}
                  </text>
                )}
                {n.done && <text className="pm-mark" x={COL.group + COL.gw - 12} y={n.y + 18}>✓</text>}
                {n.in_progress && (
                  <text className="pm-mark now" x={COL.group + COL.gw - 12} y={n.y + 18}>◐</text>
                )}
              </g>
            ))}
          </g>
        ))}

        {/* the course asked about */}
        <g className="pm-node is-target">
          <rect x={COL.target} y={tY} width={COL.tw} height="52" rx="4" />
          <text className="pm-code" x={COL.target + 13} y={tY + 21}>{target.code}</text>
          <text className="pm-sub" x={COL.target + 13} y={tY + 36}>
            {(target.title || "").length > 26 ? target.title.slice(0, 25) + "…" : target.title}
          </text>
          {target.credits && (
            <text className="pm-cr" x={COL.target + COL.tw - 13} y={tY + 21}>{target.credits} cr</text>
          )}
        </g>

        {/* what it opens */}
        {shown.length > 0 && (
          <text className="pm-grouplabel" x={COL.unlock} y={laidUnlocks[0].y - 7}>opens</text>
        )}
        {laidUnlocks.map((u) => (
          <g key={u.code} className="pm-node is-next">
            <rect x={COL.unlock} y={u.y} width={COL.uw} height="22" rx="3" />
            <text className="pm-code sm" x={COL.unlock + 10} y={u.y + 15}>{u.code}</text>
          </g>
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
      </div>
    </figure>
  );
}
