/**
 * The ace. mark — the a leans -11°, the period never does.
 *
 * Geometry is LOCKED (BRAND.md §1); this is the only place it is written down.
 * viewBox is `-44 -41 148 100`, aspect 148:100, so height must be size*100/148.
 *
 * `period={false}` drops the emerald dot for views where something else owns the
 * accent — the brand's own preview marks the nav that way: "no accent here, the
 * hero owns this view's period."
 */
/* Logo constants. These are NOT theme tokens — the tile is an ink square in
   BOTH themes (BRAND.md §1), so it must not follow --ace-ink, which inverts in
   dark. Using the token here flipped the tile to near-white in dark mode and
   swallowed the paper mark sitting on it. */
const TILE_INK = "#0A0A0A";
const TILE_PAPER = "#F6F6F6";

/**
 * The mark on its tile. The one exception to radius 0 (20%), and the only
 * place the fixed ink/paper pair is written down.
 */
export function AceTile({ size = 36, period = true, className = "" }) {
  return (
    <div
      className={`flex shrink-0 items-center justify-center ${className}`}
      style={{
        width: size,
        height: size,
        background: TILE_INK,
        borderRadius: "var(--ace-radius-tile)",
      }}
    >
      <AceMark size={Math.round(size * 0.62)} ink={TILE_PAPER} period={period} />
    </div>
  );
}

/**
 * The spelled-out `ace.` wordmark. Geometry traced from brand/logo/ace-wordmark.svg
 * (locked 2026-07-30) — do not redraw it by eye.
 *
 * UPRIGHT. Only the standalone mark leans −11°; BRAND.md §1 is explicit that the
 * spelled-out wordmark does not, so there is no rotate here.
 *
 * `width` is in px and has a FLOOR of 96 (BRAND.md §2: "aperture is 17.9u, so the
 * wordmark's minimum width is 96px — below that, use the mark"). Anything
 * smaller closes the counters up and should render <AceTile> instead.
 *
 * Letterforms use currentColor so the wordmark follows the text colour into dark
 * mode; the period is always the emerald and never recolours.
 */
export const WORDMARK_MIN_WIDTH = 96;
const WORDMARK_ASPECT = 112 / 332.93;

export function AceWordmark({ width = 104, className = "" }) {
  const w = Math.max(width, WORDMARK_MIN_WIDTH);
  return (
    <svg
      width={w}
      height={w * WORDMARK_ASPECT}
      viewBox="-54 -44 332.93 112"
      className={className}
      role="img"
      aria-label="ace"
    >
      {/* a — ring + round-capped stem */}
      <circle cx="0" cy="12" r="31" fill="none" stroke="currentColor" strokeWidth="22" />
      <rect x="30" y="-32" width="22" height="88" rx="11" fill="currentColor" />
      {/* c */}
      <path d="M 123.93 -11.75 A 31 31 0 1 0 123.93 35.75" fill="none" stroke="currentColor" strokeWidth="22" strokeLinecap="round" />
      {/* e — ring, then the crossbar whose right cap shares the ring's start centre */}
      <path d="M 211.93 12 A 31 31 0 1 0 186.31 42.53" fill="none" stroke="currentColor" strokeWidth="22" strokeLinecap="round" />
      <rect x="150.93" y="1" width="72" height="22" rx="11" fill="currentColor" />
      {/* the period — the whole identity, never recoloured */}
      <circle cx="248.93" cy="38" r="18" fill="var(--ace-period)" />
    </svg>
  );
}

export default function AceMark({ size = 16, ink = "var(--ace-ink)", period = true }) {
  return (
    <svg width={size} height={size * (100 / 148)} viewBox="-44 -41 148 100" aria-hidden>
      <g transform="rotate(-11 5 12)">
        <circle cx="0" cy="12" r="31" fill="none" stroke={ink} strokeWidth="22" />
        <rect x="30" y="-32" width="22" height="88" rx="11" fill={ink} />
      </g>
      {period && <circle cx="82" cy="38" r="18" fill="var(--ace-period)" />}
    </svg>
  );
}
