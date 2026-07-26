# Maggie animation shots — Google Flow production plan

Flow gives us **one clip per prompt, defined by a start frame and an end frame**.
So every shot below is a pair of stills. Poses marked **(new)** don't exist yet —
generate them first (prompt pack at the bottom), matching the existing five in
`landing-v2/assets/` exactly: bold ink outlines, flat cream fills, purple curls,
patterned blazer, transparent background, no text.

## How each clip gets used on the page

Two modes, both already compatible with the GSAP setup:

- **loop** — small autoplay `<video muted loop playsinline>` swapped in place of a
  static pose. Cheapest to wire; good for idle/typing loops.
- **scrub** — clip exported to a webp frame sequence, drawn to `<canvas>`, frame
  index driven by ScrollTrigger progress (Apple-style). Use only where scroll
  literally drives her motion.

Frame-extraction pipeline (per clip):

```bash
ffmpeg -i shot.mp4 -vf "scale=480:-2" -q:v 80 assets/seq/<shot>/%03d.webp
```

## Shot list (priority order)

| # | Shot | Start frame | End frame | Flow prompt sketch | Used where | Mode |
|---|------|-------------|-----------|--------------------|-----------|------|
| 1 | **wave-hello** | maggie-wave (new) | maggie-front | She lowers her waving hand and settles into holding her notepad, warm smile throughout. Flat 2D cartoon, character stays centered, transparent/plain background, no camera motion. | Hero "Meet ACE." — she waves as the headline lands | loop (play once on scene enter) |
| 2 | **front-to-point** | maggie-front | maggie-point | She tucks the notepad and raises her right hand into a confident sideways point. Same framing, flat 2D cartoon, no camera motion. | Guide's pose swap entering "Let me show you" + steps | loop (play once; replaces the crossfade hop) |
| 3 | **think-idle** | maggie-think | maggie-think | Subtle idle: she taps her chin twice, eyes drift up-left then back. Loopable — first and last frame identical. | "What makes ACE different?" big Maggie, ambient | loop |
| 4 | **typing-idle** | maggie-desk | maggie-desk | Gentle typing: fingers move on the keyboard, slight shoulder bob, screen glow flickers softly. Loopable — first and last frame identical. | bgwork desk scene, ambient | loop |
| 5 | **think-to-celebrate** | maggie-think | maggie-celebrate | Her puzzled expression breaks into a grin as both arms shoot up, double thumbs up. Small confetti pops at the peak. Flat 2D cartoon, no camera motion. | Final CTA — plays as the section scrolls in | scrub |
| 6 | **walk-cycle** | maggie-walk-a (new) | maggie-walk-b (new) | Side-profile walk: two-frame stride A→B, flat 2D cartoon, character in place (treadmill walk), loopable. | Guide "walks" during long scroll stretches between sections | scrub |
| 7 | **shrug-lost** | maggie-front | maggie-shrug (new) | She looks left then right, shoulders rise into an exaggerated "no idea" shrug, question marks pop above her head. | Statement section ("Every semester, the same panic") | loop (play once) |

Start with shots 1–4: they need only one new still (wave) and upgrade the most
visible moments. 5–7 are the second wave.

## New stills needed (generation prompt pack)

Shared prefix for every prompt — keep verbatim so the set stays consistent:

> Flat 2D cartoon illustration of Maggie: a warm middle-aged advisor with voluminous
> purple curly hair, round black glasses, teardrop earrings, purple lipstick, cream
> turtleneck, and a purple blazer covered in small cream doodles (triangles, flowers,
> squiggles). Bold black ink outlines, flat fills, minimal shading, 1950s-cartoon
> warmth. Transparent background, isolated cutout, no text, no floor, no shadow.
> Exact same character and style as the reference images.

Then per pose:

- **maggie-wave** — "…waist-up, facing the viewer, right hand raised in a friendly
  open-palm wave beside her head, left hand holding her spiral notepad at her chest."
- **maggie-walk-a** — "…full body, side profile facing right, mid-stride: right leg
  forward planted, left heel lifting, arms in natural walking swing, carrying her
  notepad in the rear hand."
- **maggie-walk-b** — "…identical side profile walk, opposite stride: left leg
  forward planted, right heel lifting, arms swung the other way."
- **maggie-shrug** — "…waist-up, facing the viewer, both palms turned up at shoulder
  height in an exaggerated cheerful shrug, eyebrows raised, mouth in a wry 'who
  knows?' smile."
- **maggie-peek** — "…leaning in diagonally from the right side of the frame as if
  peeking around a doorway: head tilted, one hand gripping the edge, big curious
  grin. Body cropped by the frame edge." (Upgrades the hero's right-edge hover
  easter egg, which currently reuses maggie-point rotated.)

Attach `maggie-front.png` + `maggie-think.png` (the originals in
`landing-v2/assets/`, not the trimmed web copies) as style references when
generating. After generation: run the same cleanup as the others — 2x downscale,
edge flood-fill background removal, trim to opaque bbox (see README).
