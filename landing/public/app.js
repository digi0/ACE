/* ============================================================================
   ace. landing — "Transit" choreography

   The signature move is a scroll-scrubbed morph of an SVG path's `d` attribute
   between a tangled and a resolved shape (technique: ~/animmaster/SVG
   Animations/5, "OnScrollPathAnimations"). It is not decoration — it is the
   thesis animated: college is a tangle, ace resolves it into a route.

   Scrub is restricted to transform / opacity / SVG `d` + stroke-dashoffset.
   Layout and text never scrub — that is what produces the motion-sick imitation.
   One curve. Enter 560ms, exit 140ms.
   ============================================================================ */
gsap.registerPlugin(ScrollTrigger);
ScrollTrigger.config({ ignoreMobileResize: true });

const EASE = gsap.parseEase("0.165,0.84,0.44,1");
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const q = (s) => document.querySelector(s);
const qa = (s) => gsap.utils.toArray(s);

const net = q(".net");
const lines = qa(".ln");

/* ---------------------------------------------------------------------------
   THE RESOLVE. Tangle -> route, scrubbed against the hero's own scroll.
   Both states are `M` + four `L` (five points) so the command sequences match;
   GSAP can only interpolate `d` when they do. SITE-SYSTEM.md §5.
   --------------------------------------------------------------------------- */
if (reduced) {
  /* never park a reduced-motion reader on the chaos frame */
  lines.forEach((el) => el.setAttribute("d", el.dataset.to));
  net.classList.add("is-resolved");
} else {
  /* The resolve is scrubbed across the hero's full 230svh, so it happens
     ON SCREEN inside the sticky viewport instead of above the fold. */
  const HERO = { trigger: ".hero", start: "top top", end: "bottom bottom" };

  lines.forEach((el, i) => {
    gsap.to(el, {
      attr: { d: el.dataset.to },
      ease: "none",
      scrollTrigger: {
        ...HERO,
        /* staggered scrub: the lines don't resolve in lockstep, so the network
           untangles the way a real one would — some strands before others.
           Keep the spread tight: heavy lag means the resolve never lands. */
        scrub: 0.3 + i * 0.06,
      },
    });
  });

  /* a line only takes its colour once it is YOURS — earned, not given */
  ScrollTrigger.create({
    ...HERO,
    onUpdate: (self) => net.classList.toggle("is-resolved", self.progress > 0.42),
  });

  /* beat 1 hands over to beat 2: the wordmark recedes, the legend arrives */
  gsap.timeline({ scrollTrigger: { ...HERO, scrub: 0.4 } })
    .to(".hero-inner", { yPercent: -10, opacity: 0, ease: "none", duration: 0.42 }, 0)
    .to(".hero-hint",  { opacity: 0, ease: "none", duration: 0.25 }, 0)
    .to(".hero-legend", { opacity: 1, ease: "none", duration: 0.3 }, 0.58);
}

/* ---------------------------------------------------------------------------
   hero intro — the letters land, the dot lands last. plays once.
   --------------------------------------------------------------------------- */
if (!reduced) {
  gsap.set([".g-a", ".g-c", ".g-e"], { opacity: 0, y: 10 });
  gsap.set(".g-dot", { opacity: 0, y: -40 });
  gsap.timeline({ delay: 0.2, defaults: { ease: EASE } })
    .to(".g-a", { opacity: 1, y: 0, duration: 0.34 }, 0.05)
    .to(".g-c", { opacity: 1, y: 0, duration: 0.34 }, 0.27)
    .to(".g-e", { opacity: 1, y: 0, duration: 0.34 }, 0.49)
    .to(".g-dot", { opacity: 1, duration: 0.06 }, 0.86)
    .to(".g-dot", { y: 0, duration: 0.44 }, 0.86)
    .to(".hero-lead", { opacity: 1, duration: 0.42 }, 1.26)
    .to(".hero-cta", { opacity: 1, duration: 0.42 }, 1.44)
    .to(".hero-hint", { opacity: 1, duration: 0.3 }, 1.7);
}

/* ---------------------------------------------------------------------------
   slabs — heads and cards assemble once on entry. Stagger by mass.
   --------------------------------------------------------------------------- */
if (!reduced) {
  qa(".slab").forEach((slab) => {
    const head = slab.querySelector(".head");
    const card = slab.querySelector(".card, .lines");

    gsap.set(head, { opacity: 0, y: 22 });
    if (card) gsap.set(card, { opacity: 0, y: 30 });

    ScrollTrigger.create({
      trigger: slab, start: "top 74%", once: true,
      onEnter: () => {
        gsap.timeline({ defaults: { ease: EASE, duration: 0.56 } })
          .to(head, { opacity: 1, y: 0 })
          .to(card, { opacity: 1, y: 0 }, "-=0.32");
      },
    });
  });

  /* ---- the route draws itself, then the destination lands ---- */
  const live = q("#rtLive");
  if (live) {
    const len = live.getTotalLength();
    gsap.set(live, { strokeDasharray: len, strokeDashoffset: len });
    /* SVG children need svgOrigin (user units), NOT transformOrigin (CSS px) —
       with the wrong one every station scales from the viewBox corner. */
    qa(".stn").forEach((s) => gsap.set(s, {
      scale: 0, svgOrigin: `${s.getAttribute("cx")} ${s.getAttribute("cy")}`,
    }));
    gsap.set(".stn-label", { opacity: 0 });

    ScrollTrigger.create({
      trigger: "#route", start: "top 58%", once: true,
      onEnter: () => {
        gsap.timeline({ defaults: { ease: EASE } })
          .to(live, { strokeDashoffset: 0, duration: 1.15 })
          .to(".stn", { scale: 1, duration: 0.34, stagger: 0.11 }, 0.25)
          .to(".stn-label", { opacity: 1, duration: 0.3, stagger: 0.11 }, 0.38);
      },
    });
  }

  /* ---- the six rails draw out, one per domain ---- */
  gsap.set(".ln-rail", { scaleX: 0 });
  ScrollTrigger.create({
    trigger: "#lines", start: "top 66%", once: true,
    onEnter: () => gsap.to(".ln-rail", {
      scaleX: 1, duration: 0.62, ease: EASE, stagger: 0.07,
    }),
  });

  /* ---- the departure board counts up ---- */
  qa("#specMajors, #specCourses, #specRules").forEach((el) => {
    const target = parseInt(el.textContent.replace(/,/g, ""), 10);
    const o = { n: 0 };
    ScrollTrigger.create({
      trigger: ".specs", start: "top 82%", once: true,
      onEnter: () => gsap.to(o, {
        n: target, duration: 1.2, ease: EASE,
        onUpdate: () => { el.textContent = Math.round(o.n).toLocaleString("en-US"); },
      }),
    });
  });

  /* ---- the bar gets out of the way on the way down ---- */
  const bar = q("#bar");
  let lastY = 0;
  ScrollTrigger.create({
    start: 0, end: "max",
    onUpdate: (self) => {
      const y = self.scroll();
      if (Math.abs(y - lastY) > 8) {
        bar.classList.toggle("is-hidden", y > 140 && y > lastY);
        lastY = y;
      }
    },
  });
}

/* The bar reads the ground beneath it. Legibility, not motion — an ink mark on
   a paper slab is invisible — so this runs even under reduced-motion. */
{
  const bar = q("#bar");
  qa(".slab-paper").forEach((light) => {
    ScrollTrigger.create({
      trigger: light, start: "top 56px", end: "bottom 56px",
      onToggle: (self) => bar.classList.toggle("on-paper", self.isActive),
    });
  });
}

/* ---------------------------------------------------------------------------
   pixel-dissolve menu — hard ~56px cells raster-wipe in one pass.
   --------------------------------------------------------------------------- */
{
  const menu = q("#menu"), grid = q("#menuGrid"), panel = q(".menu-panel");
  const btn = q("#menuBtn"), closeBtn = q("#menuClose");
  let cells = [], open = false, busy = false;

  const buildGrid = () => {
    const cx = Math.ceil(innerWidth / 56), cy = Math.ceil(innerHeight / 56);
    grid.style.setProperty("--cells-x", cx);
    grid.innerHTML = "";
    const frag = document.createDocumentFragment();
    for (let i = 0; i < cx * cy; i++) frag.appendChild(document.createElement("i"));
    grid.appendChild(frag);
    cells = Array.from(grid.children);
  };

  const setOpen = (to) => {
    if (busy || open === to) return;
    busy = true; open = to;
    btn.setAttribute("aria-expanded", String(to));
    if (to) {
      menu.hidden = false;
      buildGrid();
      if (reduced) {
        gsap.set(cells, { opacity: 1 }); gsap.set(panel, { autoAlpha: 1 });
        busy = false; closeBtn.focus();
      } else {
        gsap.timeline({ onComplete: () => { busy = false; closeBtn.focus(); } })
          .to(cells, { opacity: 1, duration: 0.01, stagger: { amount: 0.42, from: "random" } })
          .to(panel, { autoAlpha: 1, duration: 0.18, ease: EASE }, 0.46);
      }
    } else {
      const done = () => { menu.hidden = true; busy = false; btn.focus(); };
      if (reduced) {
        gsap.set(panel, { autoAlpha: 0 }); gsap.set(cells, { opacity: 0 }); done();
      } else {
        gsap.timeline({ onComplete: done })
          .to(panel, { autoAlpha: 0, duration: 0.12, ease: EASE })
          .to(cells, { opacity: 0, duration: 0.01, stagger: { amount: 0.3, from: "random" } }, 0.08);
      }
    }
  };

  btn.addEventListener("click", () => setOpen(true));
  closeBtn.addEventListener("click", () => setOpen(false));
  addEventListener("keydown", (e) => { if (e.key === "Escape" && open) setOpen(false); });
  menu.querySelectorAll('a[href^="#"]').forEach((a) => a.addEventListener("click", () => setOpen(false)));
}

/* ---------------------------------------------------------------------------
   waitlist — contract unchanged: POST {email, referral} -> {position, already}
   --------------------------------------------------------------------------- */
{
  const API = window.ACE_API_URL || "https://web-production-7ffe.up.railway.app";
  const form = q("#waitlistForm"), input = q("#wlEmail"), btn = q("#wlSubmit");
  const errEl = q("#wlError"), okEl = q("#wlDone");

  const fail = (msg) => {
    errEl.textContent = msg; errEl.hidden = false;
    btn.disabled = false; btn.textContent = "join the first 100";
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = input.value.trim();
    errEl.hidden = true;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      fail("that email doesn't look right — mind checking it");
      return;
    }
    btn.disabled = true; btn.textContent = "joining…";
    try {
      const referral = new URLSearchParams(location.search).get("ref") || "landing";
      const res = await fetch(`${API}/waitlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, referral }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || "something went wrong.");
      const n = String(data.position).padStart(3, "0");
      okEl.textContent = data.already
        ? `already on the list — you're #${n}.`
        : data.position <= 100
          ? `you're in — #${n} of the first 100.`
          : `you're in — #${n} on the list.`;
      form.hidden = true; okEl.hidden = false;
    } catch (err) {
      fail((err.message || "something went wrong — try again.").toLowerCase());
    }
  });
}
