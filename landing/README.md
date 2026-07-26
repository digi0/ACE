# ACE landing — scroll-animation edition

The ACE landing: heyparker.ai-inspired scroll *mechanics*, but the visual identity
is now fully ACE's own brand system — Bricolage Grotesque display, Caveat
handwriting, JetBrains Mono labels, paper/ink/blue/amber palette, advisor-pin
logo, desk-scene hero (chaos outside, one clean route inside the laptop), real waitlist copy, and **Maggie** throughout.
No build step — three files + assets:

- `index.html` — all content (copy from landing-v2, editable in place)
- `styles.css` — ACE tokens at the top of `:root` (palette matches ART-BRIEF)
- `app.js` — GSAP ScrollTrigger choreography, one labeled timeline per section
- `assets/` — Maggie poses copied from `landing-v2/assets`, then: downscaled 2x,
  baked-in fake checkerboard removed (edge flood-fill of neutral-light pixels
  only, so her cream fills survive), and **trimmed to the opaque bounding box**.
  The trim matters: the originals carry ~28px of dead space above her head plus
  wide transparent margins, which is what forced the old CSS crop that clipped
  her. Tight assets mean each usage just sets a width/height.

Bump `?v=` on the `styles.css` / `app.js` links in `index.html` after editing —
`python3 -m http.server` sends no cache headers, so browsers serve stale copies.

## Run it

```bash
cd parker-style-landing && python3 -m http.server 4173
```

(or just open `index.html` — fonts + GSAP come from CDNs)

## Scroll map

| Section | Effect |
|---|---|
| Hero | The student's desk: cork board + wood desk, sticky-note chaos (Kalam handwriting, editable text) around the pinned headline, pen cup / notebooks / ACE mug props; the purple laptop runs a mini ACE app (sidebar, chat, plan chips — crisp HTML, so the dive magnifies it cleanly). Scroll scatters the notes and dives into the screen, floods blue → "Meet ACE." → tagline. Hover the side margins for the peek easter eggs |
| Statement | Pinned: "Getting in is easy…" + rotating panic-questions highlight |
| Show | Arrows draw in, maggie-point presenting |
| Steps | Sticky folder cards: Upload / Ask / Stay on track, real mock UIs (audit, chat, semester alerts) |
| Background | Purple; two-column grid inside the monitor — maggie-desk bottom-left, 3 deadline cards stack on the right and pop in (grid, not absolute positioning, so she can never cover them) |
| Different | Pinned 3 phases: audit facts (pink) → school rules (yellow) → 749 majors (purple) around maggie-think |
| Marquee → Coverage → Built-by → Final | Ticker, roadmap cards w/ status chips, starburst stickers, maggie-celebrate CTA |

**Hero easter eggs**: hover the hero's left margin — a hand offers a coffee
(steam rises, cup bobs); right margin — Maggie leans in and keeps craning.
CSS-only (`.peek-zone`), hidden on touch devices. A purpose-drawn `maggie-peek`
still is queued in FLOW-SHOTS.md to replace the rotated point pose.

**Animation roadmap**: see `FLOW-SHOTS.md` — the Google Flow start/end-frame shot
list, the frame-scrub pipeline, and the prompt pack for the new Maggie stills
(wave, walk-a/b, shrug).

All timelines scrubbed and reversible. Maggie source-of-truth lives in
`landing-v2/assets/`; regenerate the cutouts by re-running the flood-fill step
if those change.
