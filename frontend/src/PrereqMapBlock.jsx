/* Prerequisite map — the first rendered answer block.
 *
 * The case for drawing this at all: the rule is "(CMPSC 122 or CMPSC 132) AND
 * (CMPSC 360 or MATH 311W)". Written as a sentence nobody parses it. Drawn as
 * two bracketed groups feeding one course, it reads in a glance.
 *
 * Data comes from the `visual.data` field on the chat stream's done event; the
 * backend only builds it when its policy decided a map was warranted, so this
 * component renders or returns null and never has to decide anything itself.
 */

const DONE = "var(--accent)";

function Node({ node, dim }) {
  return (
    <span className={`pm-node${node.done ? " is-done" : ""}${dim ? " is-dim" : ""}`}>
      <span className="pm-code">{node.code}</span>
      {node.done && <span className="pm-tick" aria-label="completed">✓</span>}
      {node.title && <span className="pm-title">{node.title}</span>}
    </span>
  );
}

export default function PrereqMapBlock({ data }) {
  if (!data?.target) return null;
  const { target, groups = [], unlocks = [], unlocks_more = 0, eligible, has_record } = data;

  return (
    <figure className="pm" aria-label={`Prerequisites for ${target.code}`}>
      <figcaption className="pm-head">
        <span className="pm-label">prerequisites</span>
        {has_record && (
          <span className={`pm-verdict${eligible ? " ok" : ""}`}>
            {eligible ? "you're eligible" : "not yet eligible"}
          </span>
        )}
      </figcaption>

      <div className="pm-body">
        <div className="pm-groups">
          {groups.map((group, i) => (
            <div className="pm-group" key={i}>
              {i > 0 && <span className="pm-and">and</span>}
              <div className="pm-row">
                {group.map((n, j) => (
                  <span key={n.code} className="pm-slot">
                    {j > 0 && <span className="pm-or">or</span>}
                    <Node node={n} dim={group.some((x) => x.done) && !n.done} />
                  </span>
                ))}
              </div>
            </div>
          ))}
          {groups.length === 0 && <p className="pm-none">No prerequisites listed.</p>}
        </div>

        <div className="pm-arrow" aria-hidden>→</div>

        <div className="pm-target">
          <span className="pm-code">{target.code}</span>
          {target.title && <span className="pm-title">{target.title}</span>}
          {target.credits && <span className="pm-cr">{target.credits} cr</span>}
        </div>
      </div>

      {unlocks.length > 0 && (
        <div className="pm-unlocks">
          <span className="pm-label">opens</span>
          <div className="pm-row wrap">
            {unlocks.map((u) => (
              <span className="pm-node is-next" key={u.code} title={u.title}>
                <span className="pm-code">{u.code}</span>
              </span>
            ))}
            {unlocks_more > 0 && <span className="pm-more">+{unlocks_more} more</span>}
          </div>
        </div>
      )}
    </figure>
  );
}
