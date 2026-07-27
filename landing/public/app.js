/* ============================================================================
   ACE landing — scroll choreography.

   The page is ONE camera move through a story, not a stack of animated
   sections. Rules enforced here:
     · The dive is driven in the LOG domain. Perceived zoom speed is
       (ds/dt)/s, not ds/dt — so easing raw scale reads "abrupt then floaty".
       We ease the EXPONENT instead, which is what makes it feel like a dolly.
     · transform-origin is measured, never hardcoded. At high scale a 2%
       error becomes a third of the viewport.
     · No bounce/elastic/back-above-1.6 anywhere. No animated box-shadow or
       filter on large elements.
     · Stillness is authored: every chapter ends with nothing moving.
   ============================================================================ */
gsap.registerPlugin(ScrollTrigger);
ScrollTrigger.config({ ignoreMobileResize: true });

const q  = (s) => document.querySelector(s);
const qa = (s) => gsap.utils.toArray(s);

/* ---------- nav: collapse to logo + actions once the desk is behind you --- */
ScrollTrigger.create({
  start: 300,
  onEnter:      () => q("#nav").classList.add("is-compact"),
  onLeaveBack:  () => q("#nav").classList.remove("is-compact"),
});

/* ---------- the waitlist: unchanged contract with the Railway backend ------
   POST {email, referral} -> {position, already}. This is live lead capture;
   it must keep working regardless of anything the animation does. */
{
  const API   = window.ACE_API_URL || "https://web-production-7ffe.up.railway.app";
  const form  = q("#waitlistForm");
  const input = q("#wlEmail");
  const btn   = q("#wlSubmit");
  const errEl = q("#wlError");
  const okEl  = q("#wlDone");

  const fail = (msg) => {
    errEl.textContent = msg; errEl.hidden = false;
    btn.disabled = false; btn.textContent = "Join the waitlist";
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = input.value.trim();
    errEl.hidden = true;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      fail("That email doesn't look right — mind checking it?");
      return;
    }
    btn.disabled = true; btn.textContent = "Joining…";
    try {
      const referral = new URLSearchParams(location.search).get("ref") || "landing";
      const res  = await fetch(`${API}/waitlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, referral }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || "Something went wrong.");
      const n = data.position;
      okEl.innerHTML = data.already
        ? `You're already on the list — <strong>#${n}</strong>. We'll be in touch.`
        : `You're in — <strong>#${n}</strong> on the list.` +
          (n <= 100 ? " That's the early-access group." : " We'll email you when your spot opens.");
      form.hidden = true; okEl.hidden = false;
    } catch (err) {
      fail(err.message || "Something went wrong — try again.");
    }
  });
}

/* ============================================================================
   Everything below is motion. Under prefers-reduced-motion we register NO
   triggers at all — the document then collapses to its natural height on its
   own, and the CSS shows every element at its resting state. No content on
   this page is motion-only.
   ============================================================================ */
const mm = gsap.matchMedia();

/* ---------------------------------------------------------------------------
   CH 1–3 · the desk, the dive, the answer — ONE pinned timeline.
   The dive and the arrival must share a timeline or the arrival reads as a cut.
   --------------------------------------------------------------------------- */
const heroRig = (targetScale, pinLength) => {
  const stage = q("#deskStage");

  /* measured vanishing point: the centre of the laptop screen, in stage
     coordinates. Must be measured UNSCALED or the percentage is wrong. */
  const setOrigin = () => {
    const prev = gsap.getProperty(stage, "scale");
    gsap.set(stage, { scale: 1 });
    const s = stage.getBoundingClientRect();
    const c = q("#laptopScreen").getBoundingClientRect();
    gsap.set(stage, {
      transformOrigin:
        `${(((c.left + c.width / 2) - s.left) / s.width * 100).toFixed(2)}% ` +
        `${(((c.top + c.height / 2) - s.top) / s.height * 100).toFixed(2)}%`,
      scale: prev,
    });
  };
  setOrigin();
  ScrollTrigger.addEventListener("refresh", setOrigin);

  const tl = gsap.timeline({
    scrollTrigger: {
      trigger: ".hero",
      start: "top top",
      end: `+=${pinLength}%`,
      scrub: 0.6,
      pin: true,
      anticipatePin: 1,
      invalidateOnRefresh: true,
      /* will-change is a LEASE, not a permanent promotion */
      onToggle: (self) => document.documentElement.classList.toggle("is-diving", self.isActive),
    },
  });

  /* ---- Ch1 · the desk at rest. Nothing moves. The dead zone is the point. */
  tl.to({}, { duration: 0.55 }, 0);

  /* ---- Ch2 · the dive. One proxy, eased in the log domain. --------------- */
  const cam = { t: 0 };
  const ez  = gsap.parseEase("power1.inOut");
  const layers = [
    [q(".softboard"), 2.3],   // furthest back, slowest
    [stage,           targetScale],
    [q(".desk-band"), 3.1],
    [qa(".desk-prop"), 4.4],  // nearest the camera, fastest — parallax
  ];
  tl.to(cam, {
    t: 1, ease: "none", duration: 2.4,
    onUpdate() {
      const e = ez(cam.t);
      layers.forEach(([el, S]) => gsap.set(el, { scale: Math.pow(S, e) }));
    },
  }, 0.55);

  /* the notes are PASSED, not thrown: they drift outward on the camera's own
     curve and leave through the frame edges. They never fade. */
  qa(".sticky").forEach((note, i) => {
    const dir = i % 2 ? 1 : -1;
    tl.to(note, {
      xPercent: dir * (120 + (i * 37) % 90),
      yPercent: -70 - (i * 29) % 70,
      ease: "power1.in", duration: 1.9,
    }, 0.6 + i * 0.06);
  });
  tl.to(".board-sheet", { yPercent: -130, ease: "power1.in", duration: 1.6 }, 0.75);

  /* the screen's own light grows until it is the page: the lamp wins */
  tl.to(".laptop-screen", { boxShadow: "0 0 120px rgba(255,231,184,.55), 0 0 240px rgba(255,201,120,.3)", duration: 1.2 }, 1.4);
  /* the hint has done its job the moment the camera starts moving */
  tl.to(".scroll-hint", { opacity: 0, duration: 0.4 }, 0.6);

  /* ---- the handoff. The plate is the same interface at real size, on the
     same near-white the laptop screen already is, so the cut is invisible. */
  tl.fromTo("#plate", { autoAlpha: 0, scale: 0.92 },
                      { autoAlpha: 1, scale: 1, ease: "power2.out", duration: 0.5 }, 2.5);
  tl.to(".desk-stage", { autoAlpha: 0, duration: 0.35 }, 2.75);

  /* the student asks. steps() reveal — never a per-character chatbot typer. */
  const question = "Can I graduate by Spring 2027?";
  const typed = { n: 0 };
  tl.to(typed, {
    n: question.length, ease: "steps(" + question.length + ")", duration: 0.7,
    onUpdate() { q("#typedQuestion").textContent = question.slice(0, Math.round(typed.n)); },
  }, 2.9);

  /* ---- Ch3 · she answers, and the daylight arrives with her -------------- */
  tl.to(".world .day",  { opacity: 1, ease: "none", duration: 0.7 }, 3.7);
  tl.to(":root", { "--lamp-power": 0.3, ease: "none", duration: 0.7 }, 3.7);
  tl.to("#plate", { autoAlpha: 0, duration: 0.4 }, 3.8);

  tl.fromTo("#answer", { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.4 }, 4.0);
  tl.fromTo(".answer-maggie", { yPercent: 9, opacity: 0 },
                              { yPercent: 0, opacity: 1, ease: "power2.out", duration: 0.9 }, 4.05);
  tl.fromTo(".answer-panel",  { y: 26, opacity: 0 },
                              { y: 0, opacity: 1, ease: "power2.out", duration: 0.7 }, 4.25);
  tl.fromTo(".answer-sign",   { opacity: 0 }, { opacity: 1, duration: 0.5 }, 4.8);

  /* ---- Ch3 ends dead still. Half a screen of nothing. ------------------- */
  tl.to({}, { duration: 0.9 });
};

/* ---------------------------------------------------------------------------
   CH 4 · the ledger. The board's own notes straighten into ordered rows.
   Pinned, because the resolve needs a stationary frame.
   --------------------------------------------------------------------------- */
const ledgerRig = (pinned) => {
  /* text reveals are never scrubbed — text that fades back out on scroll-up
     reads as a bug, not as motion */
  gsap.from(".clarity .chapter-h, .clarity .chapter-p, .clarity .chapter-spec", {
    y: 26, opacity: 0, duration: 0.6, ease: "power2.out", stagger: 0.08,
    scrollTrigger: { trigger: ".clarity", start: "top 78%", once: true },
  });

  const cfg = pinned
    ? { trigger: ".clarity", start: "top top", end: "+=200%", scrub: 0.6, pin: true,
        anticipatePin: 1, invalidateOnRefresh: true }
    : { trigger: ".clarity", start: "top 65%", once: true };

  const tl = gsap.timeline({ scrollTrigger: cfg });

  /* the sheet opens EMPTY — outline and dashed rules, no answers yet */
  tl.fromTo(".plan-sheet", { y: 70, opacity: 0 },
                           { y: 0, opacity: 1, ease: "power2.out", duration: 0.7 }, 0.3);

  /* each row: the student's own handwriting straightens out of its sticky
     tilt, then the answer lands beside it. Clutter becoming order, literally. */
  qa(".plan-row").forEach((row, i) => {
    const at = 0.95 + i * 0.42;
    tl.fromTo(row.querySelector(".row-note"),
      { x: -26, rotate: -5, opacity: 0 },
      { x: 0, rotate: 0, opacity: 1, ease: "power2.out", duration: 0.45 }, at);
    tl.fromTo(row.querySelector(".row-answer"),
      { x: 14, opacity: 0 },
      { x: 0, opacity: 1, ease: "power2.out", duration: 0.35 }, at + 0.22);
  });

  tl.fromTo(".plan-next", { y: 12, opacity: 0 },
                          { y: 0, opacity: 1, ease: "power2.out", duration: 0.4 }, 2.9);
  tl.fromTo(".plan-maggie", { y: 40, opacity: 0 },
                            { y: 0, opacity: 1, ease: "power2.out", duration: 0.6 }, 3.05);
  tl.to({}, { duration: 0.6 });   /* still before the chapter releases */
};

/* ---------------------------------------------------------------------------
   CH 5 · the watch. Unpinned — one-shot reveals only. Scroll velocity is
   already the chapter's clock; a scrub would make it twice as expensive to read.
   --------------------------------------------------------------------------- */
const watchRig = () => {
  gsap.from(".watch-copy > *", {
    y: 24, opacity: 0, duration: 0.6, ease: "power2.out", stagger: 0.08,
    scrollTrigger: { trigger: ".reminders", start: "top 78%", once: true },
  });

  /* the past draws in from behind you; time arriving, not being created */
  gsap.from(".rail-past", {
    scaleX: 0, transformOrigin: "left center", duration: 0.7, ease: "power2.out",
    scrollTrigger: { trigger: ".rail-wrap", start: "top 76%", once: true },
  });
  gsap.from(".mark.is-past", {
    opacity: 0, duration: 0.4, stagger: 0.12, delay: 0.25,
    scrollTrigger: { trigger: ".rail-wrap", start: "top 76%", once: true },
  });

  /* the future is a FADE, not a draw: NOV 3 was always queued. Seeing it
     sitting there quietly from the first frame is the product. */
  gsap.from(".rail-future, .mark:not(.is-past), .rail-today", {
    opacity: 0, y: 6, duration: 0.5, ease: "power2.out", stagger: 0.09, delay: 0.35,
    scrollTrigger: { trigger: ".rail-wrap", start: "top 76%", once: true },
  });

  /* every card enters identically. Urgency is carried by content and one
     clay dot — never by making the deadline card louder. */
  qa(".watch-card").forEach((card, i) => {
    gsap.from(card, {
      y: 18, opacity: 0, duration: 0.55, ease: "power2.out", delay: 0.5 + i * 0.18,
      scrollTrigger: { trigger: ".rail-wrap", start: "top 72%", once: true },
    });
  });

  gsap.from(".desk-maggie", {
    y: 40, opacity: 0, duration: 0.7, ease: "power2.out",
    scrollTrigger: { trigger: ".desk-maggie", start: "top 92%", once: true },
  });
  gsap.from(".cover-slip", {
    y: 30, opacity: 0, duration: 0.6, ease: "power2.out",
    scrollTrigger: { trigger: ".cover-slip", start: "top 86%", once: true },
  });
};

/* ---------------------------------------------------------------------------
   CH 6 · morning at the same desk. Action first, decoration last, then the
   page stops moving before it asks anyone to type.
   --------------------------------------------------------------------------- */
const dawnRig = () => {
  const tl = gsap.timeline({
    scrollTrigger: { trigger: ".dawn", start: "top 62%", once: true },
  });
  tl.from(".cta-card",   { y: 28, opacity: 0, duration: 0.6, ease: "power3.out" }, 0)
    .from(".dawn-board", { y: 24, opacity: 0, duration: 0.6, ease: "power2.out" }, 0.1)
    .from(".plan-card",  { y: -18, rotate: -4, opacity: 0, duration: 0.5, ease: "back.out(1.4)" }, 0.25)
    .from(".pc-row",     { x: -10, opacity: 0, duration: 0.3, stagger: 0.1, ease: "power2.out" }, 0.5)
    .from(".dawn-maggie", { y: 40, opacity: 0, duration: 0.7, ease: "power2.out" }, 0.6)
    .from(".maggie-note", { opacity: 0, duration: 0.5, ease: "power2.out" }, 1.05);
};

/* ---------------------------------------------------------------------------
   Breakpoints. Desktop keeps two pins (hero, ledger) with an unpinned chapter
   between them. Mobile keeps ONE pin — the hero — and shortens it; a 375px
   screen cannot carry a two-column pinned frame.
   --------------------------------------------------------------------------- */
mm.add(
  {
    isDesktop: "(min-width: 901px) and (prefers-reduced-motion: no-preference)",
    isMobile:  "(max-width: 900px) and (prefers-reduced-motion: no-preference)",
  },
  (ctx) => {
    const { isDesktop } = ctx.conditions;
    /* portrait: the laptop screen is a bigger share of the frame, so the
       camera needs far less travel to arrive */
    heroRig(isDesktop ? 5.6 : 3.2, isDesktop ? 340 : 190);
    ledgerRig(isDesktop);
    watchRig();
    dawnRig();
  }
);

/* debounced — an undebounced resize listener refreshes on every pixel of an
   iOS URL-bar slide */
let rt;
window.addEventListener("resize", () => {
  clearTimeout(rt);
  rt = setTimeout(() => ScrollTrigger.refresh(), 150);
});
