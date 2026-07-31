# ace. — the site system ("Transit")

The marketing site's design system. **This is not Zero Chroma and is not meant to be.**
`BRAND.md` §5 left "does the marketing layer get the same restraint as the product?"
open. This file answers it: **no.** Signed off by Raghav 2026-07-31.

---

## 1. Why the divergence exists

Zero Chroma is a **product-UI** system, and it is correct there. Six greys plus one
emerald "resolved" cue is right for a student working inside the app at 2am: calm
is the job, and the accent earns its meaning by repeating in exactly one role until
the student learns it.

A landing page is seen **once, for three seconds, on a phone.** Conditioning cannot
happen in one view, so the one-accent law costs the site everything and buys it
nothing. Applied faithfully to the landing, it produced a page that was accurate to
the brand and dead on arrival.

So the layers diverge, deliberately and in writing.

## 2. The contract — what crosses the boundary

**Locked. Identical in both layers. Never negotiate these:**

- the `ace.` mark and its geometry (`brand/logo/`) — including "never recolour the dot"
- **emerald `#00875A` means *resolved*, and only that.** It is never a line, never
  decoration, never a loading/empty/error state.
- lowercase voice, short sentences, no exclamation marks
- mono over real numbers only — never over a marketing claim. Zero-pad everything.
- radius 0 (the logo tile's 20% stays the one exception)
- one easing curve; exits pinned short

**Site-only. The app does NOT get these:**

| the site may | the app may not | why |
|---|---|---|
| six line colours | — | colour carries the *ecosystem* claim; the app doesn't make that claim |
| a dark ground by default | — | the site is a poster; the app is a workspace |
| glow on route nodes | — | arrival should feel like arrival once, not every session |
| display type past 28px | capped at 28px | the site needs a display tier; the app needs to be read |

Anything not in that table applies to both layers.

## 3. The decisive axis — colour as wayfinding

ACE is the navigation layer for college. So the site's visual language **is**
navigation, and colour is never decorative: **every hue is a line, and every line is a
domain of student life.**

This is `BRAND.md`'s own illustration law scaled up rather than abandoned —
*grey = possible, ink = yours, emerald = the point.*

| line | token | domain | example question |
|---|---|---|---|
| academic | `#4D7CFE` | courses, prereqs, audits | which gen-ed clears my last requirement? |
| logistics | `#FF9F1C` | printing, parking, transit | where can i print at 2am? |
| money | `#FF5A5F` | bursar, aid, holds | how do i set up a payment plan? |
| places | `#2EC4E6` | dining, hours, buildings | is anything open to eat right now? |
| people | `#B08CFF` | clubs, orgs, advisors | is it too late to join a club? |
| beyond | `#FFD23F` | internships, abroad, career | what do i need for a spring internship? |

**Emerald is not a seventh line.** It is the destination node that lands on top of
whichever line you are riding. That is how the site gets six colours without spending
the one mechanism the brand actually owns.

**The ghost rule survives:** `--ghost` draws every path the catalog allows. A line only
takes its colour once it is *yours*.

## 4. Type

Helvetica Neue is the wayfinding typeface — the NYC subway runs on it. It is already
the brand's sans, so the site's display tier costs zero webfont loading and is
justified rather than chosen.

| tier | size | leading | tracking | weight |
|---|---|---|---|---|
| display | `clamp(56px, 11vw, 148px)` | 0.92 | −0.04em | 500 |
| lead | 24px | 1.25 | −0.02em | 400 |
| body | 16px | 1.45 | 0 | 400 |
| mono label | 11px | 1.0 | +0.18em | 500, uppercase |

Display:body tops out at **9.25×** — past the ≥6× floor, clear of the 2–3× dead band.
**There is a deliberate hole between 24 and 56px.** Do not fill it.

Mono is the departure board: counts, codes, times, station names. Never a claim.

## 5. Space & motion

- one unit: `4px`. Quantise everything.
- section padding: `120px` desktop / `72px` under 780px.
- one curve: `cubic-bezier(.165,.84,.44,1)`.
- **enter 560ms, exit 140ms** (4:1). Symmetric timing is why most motion reads cheap.
- scrub is restricted to `transform`, `opacity`, and SVG `d`/`stroke-dashoffset` —
  never layout, never text.

### The signature move

Scroll-scrubbing an SVG path's `d` attribute between a tangled and a resolved shape
(technique from `~/animmaster/SVG Animations/5`). It is the thesis animated: college
is a tangle, ace resolves it into a route.

**Constraint:** morph pairs must share an identical command sequence. Every network
path is `M` + four `L`s — five points, always. Change the count in one state and you
must change it in both.

## 6. Accessibility floors — not negotiable against any of the above

- line colour is never the only carrier: every line is also **named in text**.
  Six hues are unusable to a colourblind student on their own.
- destination emerald on the dark ground is used at **graphic scale only** (nodes,
  fills), where the 3:1 floor applies — never as small text.
- `prefers-reduced-motion` gets the **resolved** state, not the tangle. The page must
  never park a reduced-motion reader on the chaos frame.
