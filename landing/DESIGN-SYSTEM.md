# ace. landing — the system

Everything settled in the 2026-08-02 working session, in the order it was decided.
Supersedes `brand/SITE-SYSTEM.md` (the "Transit" wayfinding system, abandoned).

`brand/BRAND.md` still governs **the mark**. It no longer governs this site.

---

## 1 · Who and how

- **Reader:** a college student, 18–24, any year. Not a segment — one person on a
  phone who was sent a link.
- **Channels:** word of mouth first, then SEO and Instagram. Only word of mouth
  lands on the homepage; SEO lands on a *question*, Instagram lands from content
  that already persuaded. Design for the homepage, but don't assume it's the door.
- **The ask:** join the waitlist. **The gate stays** — it's a deliberate brand
  asset, the early-access play.
- **Consequence of the gate:** exclusivity only works if people can *see* what
  they're excluded from. So the page must **show the product working**, not
  describe it. Four previous attempts all argued; none demonstrated. That was the
  core failure.

## 2 · Register

**Students win.** Credibility for investors comes from craft, specificity and
proof — never from getting quieter. A consumer college product that looks like
enterprise software scores *worse* with a good investor, not better.

Every earlier version reached for credibility by becoming more restrained. Wrong
instrument. That oscillation is what produced four dead pages.

## 3 · Positioning

> **ACE is the friend who's a year ahead — for everyone.**

Not a painkiller for panic. Nobody aspires to be less stressed; a page built on
stress can't aspire, because its emotional peak is the absence of a bad feeling.
This sells **belonging and competence** instead, it's social (college is social),
and it explains breadth for free — a friend a year ahead knows about food *and*
deadlines *and* clubs.

Lines this opens: *someone always knows. now it's you.* · *the friend who's a year
ahead* · *everything the upperclassmen already know.*

## 4 · Page structure

**Wedge first, breadth second.**

The wedge is the only genuine wow: **ACE knows your situation** — major, catalog
year, what's passed, what's left. *"Can I still graduate on time if I drop this?"*
is a question ChatGPT cannot answer and an advisor takes two weeks to.

But the wedge needs the student's own audit, which a stranger hasn't uploaded. So:

- **Perform the wedge.** Scripted, one specific student's real case. What makes a
  demo smell fake is being *generic* — "CMPSC 465, handbook p.14, 12 credits left"
  reads real because it is.
- **Live box under breadth.** Breadth questions ("is anything open to eat right
  now?") need no personal data and can be answered live and cheap. They get one
  real answer, feel it work, *then* hit the gate. Scarcity you can see.

Skeleton: **hero → performed wedge → breadth + live box → gate.**

## 5 · The bar for the hero

Word of mouth doesn't run on people who scroll. It runs on people who
**screenshot**.

> **What's the one frame someone sends to their group chat?**

It must survive with no context, at thumbnail size, seen by someone who wasn't
looking for it. Slogans die at that bar. The performed wedge — a real question and
a real answer with real course codes and a cited page — survives it, and doubles
as the Instagram content engine.

## 6 · Colour — palette B, "campus spectrum"

**Zero Chroma governs the mark only.** Released as a site constraint 2026-08-02.

| role | value |
|---|---|
| ground | `#FBF6EC` cream — **never white** |
| ink | `#14120E` — never black |
| rule | `#E3DCCB` |
| dim text | `#57524A` |
| emerald | `#00875A` — resolved, and the logo's colour |
| orange | `#F0620C` |
| red | `#E5323B` |
| cobalt | `#1B49E4` |
| yellow | `#FFC53D` |

**The discipline that stops it becoming confetti: one colour owns a SECTION, not
an element.** Each screen takes a single colour at full force; the others stay off
it entirely. Wide across the page, narrow within any view.

**The accent must own at least one whole screen.** An accent that only ever
appears as a 4px dot isn't restraint, it's absence — that is precisely what read
as "bland" three times running.

## 7 · Type

All self-hosted from Fontshare, free EULA, in `public/type/fonts/`. Chosen by
rendering 39 candidate families and looking at them.

| role | face | why |
|---|---|---|
| display | **Recia** 300–700 | sharp, editorial, authoritative. reads like a publication with a point of view |
| information | **Switzer** 300–900 | cleanest workhorse on Fontshare; handles course codes and figures better than Satoshi |
| receipts | **Tabular** 400–700 | purpose-built for figures. `087/120`, `CMPSC 465`, `P.14` |

Recia is the *authority* choice — warmth has to come from colour, copy and motion,
not from the letterforms.

### Ladder

| tier | size | leading | tracking | weight |
|---|---|---|---|---|
| display | `clamp(40px, 7vw, 104px)` | 0.94 | −0.03em | Recia 700 |
| lead | 20px | 1.45 | −0.01em | Switzer 400 |
| body | 16px | 1.55 | 0 | Switzer 400 |
| receipts | 11px | 1.0 | +0.14em, uppercase | Tabular 400 |

**Deliberate hole between 20 and 40px. Do not fill it.**

## 8 · Ink — punctuation, never substrate

Four hand-drawn marks, drawn by Raghav (see `INK-KIT.md`): `audit`, `circle`,
`arrow`, `check`.

> **If two ink marks are visible in one viewport, one of them is wrong.**

Cut from 23 to 4 at Raghav's call — *"a website has to at the end of the day look
like a website."* Correct. The structure carries the site; ink annotates it.

The ink concentrates into **one signature moment**: a marked-up degree audit, as
if a friend a year ahead annotated the document you can't read.

## 9 · The owned asset

**Not a mascot — the answer artifact.** The question, the verdict, the route, the
citation. One object doing five jobs: the demo, the screenshot, the Instagram
post, the investor slide, and the product itself.

Design it obsessively. It's the most valuable surface on the page.

## 10 · Craft rules — learned from heyparker, not copied from it

1. **One line weight everywhere.** Borders, rules, dividers, icon strokes, ink.
   Pick it once, never deviate. This is the coherence engine and it's free.
2. **The ground is never white.** Cool greys read as software; warm reads as paper.
3. **Register collision is the design idea.** Serif carrying emotion, grotesque
   carrying information, mono carrying receipts, one hand-drawn human mark. Four
   registers, strict jobs, no overlap. When everything agrees, it's boring — which
   is exactly what happened to the transit map.
4. **Grading, not cutting, makes mixed media work.** A cut-out photo must be
   colour-graded *into* the palette or it always looks pasted.
5. **Motion is spatial, not decorative.** Every move reveals the next thing. Things
   fading up in place is why the earlier builds felt like slideshows.
6. **Smooth scroll is required.** Native scroll arrives in discrete jumps and any
   scrubbed animation stutters against it. Lenis or equivalent. Its absence is a
   large part of why our floppy-insert clone broke and Parker's is liquid.

## 11 · Still open

- **Layout grammar.** Editorial density as the spine with a few full-screen scene
  moments punched in, versus scene-per-viewport throughout. Leaning the former —
  airy scenes with nothing in them *is* blandness, close to by construction.
- **Where a colour owns a full screen**, and which one.
- **Whether we shoot photography** — real objects, cut out and graded. The one
  route to real imagery needing neither an illustrator nor generation.

## 12 · Dead ends — do not revisit

- **Zero Chroma applied to the site.** Six greys plus one dot. Read as bland three
  separate times. It's a product-UI system.
- **Apple capability slabs.** Apple grammar minus a photogenic product equals a
  list of feature cards.
- **The transit / wayfinding diagram.** Information design where emotional design
  was needed. Explained; didn't connect.
- **The 2am desk.** Sells relief from stress. Nobody aspires to that.
- **Placeholder art.** Grey rectangles with a noise filter are slop. Either real
  art or none.
- **Generated hand-drawn illustration.** The worst style for generative models —
  it imitates a hand rather than being one.
