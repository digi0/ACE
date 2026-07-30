# ace. — brand system

Built 2026-07-29/30 over sixteen rounds. This file is the source of truth and the
handoff: everything **locked** is settled, everything **provisional** is the next
session's work.

---

## 1. The mark — LOCKED

A geometric single-story lowercase **a**, leaning, followed by an oversized
**orange period** on the baseline.

**The a leans −11°. The box and the period never tilt. The spelled-out wordmark
never tilts.** (The letter leans when it's alone; the word stands together.)

| | value |
|---|---|
| Bowl | `circle cx=0 cy=12 r=31`, stroke `22` (0.71R) |
| Stem | `rect x=30 y=-32 w=22 h=88 rx=11` (round ends) |
| Lean | `rotate(-11 5 12)` — applied to bowl + stem only |
| Period | `circle cx=82 cy=38 r=18` (0.58R), bottom on baseline `y=56` |
| Ink | `#0A0A0A` — never pure black |
| Period | `#FF5A1F` — identical in light and dark |
| Paper | `#F6F6F6` |
| Clearspace | one bowl-radius (R) all sides |
| Minimum | 24px — below that use the favicon cut (dot grows to 0.7R = r22, cy34) |

**Wordmark** (`ace.`, upright, W4 all-round system): every terminal is a round cap,
matching the mark's round-ended stem and the dot, so mark + tile + wordmark are one
family. `c` = arc ±50° round caps @ center 104. `e` = ring arc 0°→80° round caps @
center 180.93, plus bar `rect(150.93,1,72,22,rx11)` whose right cap center coincides
with the arc's start cap at `(ec+31,12)` — that coincidence is deliberate and load
bearing: it produces ONE clean 11u nose. Dot `r18 @(248.93,38)`.
viewBox `-54 -44 332.93 112`. Optical gaps a-c `10u` / c-e `4u` / dot `8u`.
**Aperture is 17.9u, so the wordmark's minimum width is 96px** — below that, use the
mark or favicon instead.

Don'ts: never recolour the dot, rotate the whole mark, outline it, or detach the dot
from the baseline.

### Files — `brand/logo/`
| file | use |
|---|---|
| `ace-mark.svg` | naked mark — headers, merch, box-free contexts |
| `ace-tile.svg` | primary tile, light surfaces |
| `ace-tile-dark.svg` | dark UI — ink tile + paper-alpha hairline |
| `ace-tile-dark-inverted.svg` | OS dark-mode app icons |
| `ace-favicon.svg` | 16–24px cut |
| `ace-wordmark.svg` / `-dark.svg` | upright `ace.` |

Open `brand/logo/index.html` for a visual index at real sizes.

---

## 2. The language — Zero Chroma — LOCKED

Six greys, no hue, plus the period. Chosen from eight fully-specified candidates
(see `reference/eight-design-languages.html`; Ember Ink was explicitly rejected).

Tokens live in **`brand/tokens.css`** — import it, don't retype the values.

The rules that make it work:

- **Orange appears once per view, and it is always the period.** Send button, due
  date, destination, done. A second orange element in a view means one is wrong.
  This is enforceable in review and impossible to copy without copying the whole
  philosophy.
- **Cards sit lighter than the page** (`#FFFFFF` on `#F6F6F6`) — never raised by
  shadow. Zero box-shadows on the marketing layer. No gradients, anywhere.
- **Text never exceeds 28px; the wordmark carries display scale.** This is the
  "go flat and let something non-typographic carry the hero" strategy.
- **Sans speaks, mono counts.** Mono only over real readouts (087/120, WEEK 04,
  EXIT CODE 0) — never over marketing claims. Zero-pad every number.
- **Radius 0 globally.** The logo tile is the one exception (20%).
- **One easing curve** (`--ace-ease`) for ~80% of motion. Exits pinned at ~120ms;
  only *enter* durations scale with the size of the arriving thing.
- **Body leading 1.4. Measure 35–58ch, capped on the paragraph, not the container.**

### Voice
Lowercase. Short sentences. No exclamation marks — confidence doesn't shout.
The orange period lands on the line that *resolves* the stress; grey periods carry
the rest. One orange period per screen.

> college, sorted. · your 2am question. answered. · failed it? rerouted. ·
> 12 credits left. you're fine. · 0 warnings.

### Illustration — grey = possible · ink = yours · orange = the point
Ghost grey draws every path the catalog allows; ink draws the student's actual route;
the orange dot marks the destination.

**The law, learned the hard way:** *lines run centre-to-centre and nodes sit on top —
the route is never broken. Style may not disconnect what the feature connects.* An
earlier draft floated the route segments apart for aesthetic reasons and destroyed
the one thing the feature exists to communicate. Improvise the theme around the
function; never apply it over the function.

See `brand/brand-book.html` (full book: construction, clearspace, don'ts, colour
proportion strip, type, voice, illustration set, three campus posters, applications)
and `brand/system-preview.html` (the language applied to real ACE surfaces: hero,
chat, dashboard, prereq route, stats, merch).

---

## 3. Shipped — LOCKED

Commit `3916de6` replaced the grad-cap across the product:

- `frontend/public/favicon.svg` + all PWA/apple-touch PNGs (**rasterized from the
  SVG** — regenerate by rendering `<img src=favicon.svg width=N>` at
  `--window-size=N,N --screenshot`; the maskable variant uses a full-bleed,
  no-radius tile at `scale(1.72)` for Android's safe zone)
- `frontend/src/App.jsx` — `AceMark({size, ink})` replaces `GradCapIcon`.
  **viewBox is `-44 -41 148 100`, aspect 148:100 — height must be `size*100/148`.**
- `frontend/src/Sidebar.jsx`, `frontend/src/LoginPage.jsx` (the login page had been
  showing a *clock* icon)
- `frontend/src/index.css` — logo tiles blue→ink, and `.ace-logo-box` finally has a
  CSS rule; it had none, so the top-bar box was transparent and its white strokes
  were invisible
- `landing/` — nav + footer take the naked mark; the two glyphs inside the
  illustrated app mockups sit at 8–12px (below the 24px minimum) so they became
  miniature ink tiles. Brand name blue→ink so it stops fighting the orange dot.

**Gotcha:** `landing/index.html` links `/styles.css?v=N` — a query-string
cache-buster. **Bump N on every landing CSS edit** or open browsers keep the stale
sheet. Also, that absolute path means `file://` previews render unstyled; serve over
HTTP to QA the landing.

---

## 4. Next — PROVISIONAL, this is the pickup point

The goal: **remodel the landing site and the product UI around Zero Chroma.**
Nothing below has been started.

1. **Landing (`landing/`)** is still the old brand — blue/amber/purple, Bricolage
   Grotesque, the desk-scene hero. The new mark now sits inside it, which is a
   deliberate but temporary mismatch. Port it to Zero Chroma: swap the palette for
   `tokens.css`, drop the coloured accents to greys, let the orange survive only as
   the period, and rebuild the hero around the oversized `ace.` wordmark.
2. **Product UI (`frontend/src/`)** — `index.css` is ~3200 lines with a `#2563eb`
   blue accent throughout, plus `App.css` and `responsive.css`. Migration path:
   import `tokens.css`, then replace the blue accent role by role, auditing each
   against the one-orange-per-view law (the chat send button is the canonical
   period; most other blue is *not* an accent role and should become ink or grey).
   Preserve the desktop-isolation contract in `responsive.css` (@768px).
3. **The illustration system** — build the route/pile/doors/week pieces as real
   components for the dashboard and prereq map, per the illustration law above.
4. **Dark mode** — only the logo treatment is signed off. The dark tokens in
   `tokens.css` are provisional and need a real design pass.
5. Poster/merch artwork in the brand book is design-only; nothing is production-ready
   for print.

Open questions to settle with the founder before building:
- Does Zero Chroma apply to the *whole* product, or does the app keep more warmth
  than the marketing site?
- Bento Soft (`reference/eight-design-languages.html`, language 07) was noted as the
  natural fit for the dashboard specifically — worth revisiting for that surface.
