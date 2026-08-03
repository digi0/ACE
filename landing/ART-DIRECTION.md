# ace. landing — art direction

**"The light that's on at 2am."**

Companion to `brand/SITE-SYSTEM.md` (type, colour, motion). This file governs the
pictures. **Raghav generates these in Gemini / Google Flow. Claude does not
generate art and does not touch Higgsfield credits.**

---

## 1. The anchor — read this before using any prompt below

The failure mode of generated art is that the model averages. Give it "greyscale
illustration of a student desk" and it returns the mean of every stock
illustration ever made. **The fix is to name a tradition it can stand inside.**

Ours is **Edward Hopper** — *Nighthawks*, *Office at Night*, *Automat*, *Morning
Sun*. Hopper painted exactly one thing over and over: **artificial light in a
dark interior, a person alone, patient, unresolved.** That is not a decorative
reference. It is the emotional thesis of this product, already painted, eighty
years ago.

From Hopper we take:
- **light as the subject.** The lit thing is the composition. Everything else is
  the dark it sits in.
- **the geometry of a lit rectangle** — a window, a screen — cutting a dark room.
- **stillness that reads as waiting, not as emptiness.**
- **flat planes of colour, hard shadow edges, no fussy detail.**

From **risograph / 2-colour zine printing** we take the surface: visible halftone,
slight misregistration, ink sitting *on* paper. That texture is what separates
"printed" from "rendered," and rendered is what reads as AI.

Anything that looks like a 3D render, a glossy vector, or a Behance "flat
illustration" is wrong and should be regenerated, not fixed.

## 2. Palette — non-negotiable

Six greys, `#0B0D10 · #16191D · #39404A · #8A929C · #C9CED4 · #F4F5F7`, and one
colour: emerald `#00875A` / lit `#00B876`.

**Emerald is only ever emitted light** — a screen, a lamp, a lit window, a status
LED, dawn. Never a painted object, never a shirt, never a mug. If the emerald is
touching something that isn't glowing, it's wrong.

**Zero Chroma is not being obeyed here, it's being adapted.** The greys stop
being a UI restriction and become an illustration palette; the accent stops being
a rule and becomes the one light still on. Same law, emotional register.

## 3. Format

- **One strong image per scene.** Not five transparent layers — that fights the
  tool. Claude animates a single flat image with camera moves (push, pan, crop
  reveal) the way film moves across a matte painting, and choreographs type over it.
- 16:9, at least 2400px wide. PNG or high-quality JPG.
- **If** a scene turns out to want real depth, the cheap way to get it is to
  generate *the same scene at two camera distances* and cross-fade between them.
  Easier than masking, and it reads as a dolly.
- Deliver into `landing/public/art/` with the filenames below.

---

## 4. PROMPTS — paste-ready

Run **`01-desk` first, alone.** If its light, texture and restraint are right,
everything else will be. If not, we adjust one prompt having spent one
generation. Never batch-generate into an unproven look.

### `01-desk.png` — the opening. 02:14.

```
An Edward Hopper painting of a student's desk at 2am, seen from the first-person
point of view of someone sitting at it. In the manner of "Office at Night" and
"Automat": flat planes, hard shadow edges, stillness that reads as waiting.

The only light source in the entire image is an open laptop screen, glowing a
deep emerald green. It cuts a lit rectangle into a dark room. Everything the
light does not reach falls into charcoal and slate grey. The image is entirely
greyscale except for that green light and the glow it throws — no other colour
anywhere.

On the desk: a thick stapled printout, loose pages, three sticky notes, a cold
mug of coffee, a phone lying face down. A dark window at the left edge with a
few faint distant lights beyond it.

Printed as a two-colour risograph — visible halftone dots, slight ink
misregistration, matte paper texture. Ink sitting on paper, not rendered.

No people's faces. No readable text. No logos. No lens flare. Not a 3D render,
not a glossy vector illustration.
```

### `02-audit.png` — the twelve-page PDF

```
An Edward Hopper style painting, greyscale, of a thick stapled university
document lying open on a dark desk under a single overhead light. Twelve pages
of dense administrative text, rendered as grey ruled texture rather than
readable words. The paper is the brightest thing in a dark room.

One line on the page is lit emerald green, as if a light is passing under it.
That green is the only colour in the image.

Two-colour risograph print, visible halftone, slight misregistration, matte
paper. Flat planes, hard shadows. No faces, no logos, no legible words. Not a
3D render.
```

### `03a-night.png` / `03b-morning.png` — the payoff pair

Generate these as a **matched pair, same composition, same framing**. `03a` is
the Flow start frame, `03b` the end frame.

```
[03a — NIGHT]
An Edward Hopper painting of a dark student bedroom at 2am, wide view. A desk
against the wall, an open laptop the only light source, glowing emerald green
and throwing a hard lit rectangle across the floor. Deep charcoal shadow
everywhere else. Entirely greyscale except the green screen light. Two-colour
risograph, visible halftone, matte paper, flat planes, hard shadow edges.
Nobody in frame. No text, no logos. Not a 3D render.
```

```
[03b — MORNING]
The exact same room, same desk, same camera position and framing, at 6:40am.
Dawn light now floods in from a window on the left; the room is fully legible in
warm greys. The laptop is closed. The scattered pages have been squared into one
neat stack. Everything is greyscale — the only colour is one small emerald
indicator light on the closed laptop. Calm, resolved, morning. Two-colour
risograph, visible halftone, matte paper. Nobody in frame. No text, no logos.
Not a 3D render.
```

### The six vignettes — `v-academic` … `v-beyond`. 1:1, 1200px.

Same base, swap the final line. Each is a *place*, empty, with exactly one
emerald light.

```
An Edward Hopper painting, greyscale, of {PLACE}. Empty, still, late. The only
light source is {LIGHT}, glowing emerald green — the only colour in the image.
Everything else is charcoal and slate. Flat planes, hard shadow edges, a mood of
patient waiting. Two-colour risograph print, visible halftone, slight
misregistration, matte paper texture. No people, no text, no logos. Not a 3D
render, not a flat vector illustration.
```

| file | {PLACE} | {LIGHT} |
|---|---|---|
| `v-academic` | an empty lecture hall at night, rows of seats | the exit sign above the door |
| `v-logistics` | a campus print room at 2am, one printer mid-job | the printer's status lamp |
| `v-money` | a bursar's service window, closed, blind half-drawn | the call light beside the window |
| `v-places` | a dining hall at closing, chairs upturned on tables | a heat lamp over the empty counter |
| `v-people` | a club fair table at dusk, folding table, scattered flyers | a single string light above it |
| `v-beyond` | a departures board in an empty student union hallway | one lit row on the board |

### `04-morning.mp4` — Google Flow, ≤10s

- **Start frame:** `03a-night.png`  · **End frame:** `03b-morning.png`
- **Motion:** `slow, almost imperceptible push in. Dawn light rises gradually
  from the left. No camera shake, no cuts, nobody enters frame.`
- **Deliver:** MP4, H.264, ≤4MB, **no audio.** Claude scroll-scrubs it, so it
  must read correctly at any playback speed including reversed.

---

## 5. If the generated look never gets there

The most slop-proof art available costs nothing: **shoot it.** A real photograph
of a real desk at 2am, converted to the six greys with the screen left emerald,
is un-fakeable and is exactly the editorial move — magazines have done
colour-isolation for decades. You are surrounded by the raw material: your desk,
the print room, the dining hall at closing.

If you shoot, shoot in the dark with the real light source in frame, hold the
camera still, and don't light anything else. Claude does the grey conversion and
the colour isolation.

## 6. Rejecting a generation

Regenerate rather than accept, if:
- there is any colour other than emerald
- the emerald is on something that isn't emitting light
- it looks rendered, glossy, or 3D
- the texture is clean — no halftone, no misregistration means it will read as AI
- it is busy. Hopper is empty. Empty is the point.
