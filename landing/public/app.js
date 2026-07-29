/* Scroll choreography — GSAP ScrollTrigger.
   Every timeline is scrubbed, so scrolling backwards reverses everything. */
gsap.registerPlugin(ScrollTrigger);

/* size the statement rotator to its longest phrase so nothing clips */
{
  const rotator = document.querySelector(".rotator");
  const w = Math.max(...[...rotator.querySelectorAll(".rot-word")].map(el => el.offsetWidth));
  rotator.style.minWidth = w + 4 + "px";
}

/* ---------- nav: collapse to logo + CTA once you leave the hero top ---------- */
ScrollTrigger.create({
  start: 300,
  onEnter: () => document.getElementById("nav").classList.add("is-compact"),
  onLeaveBack: () => document.getElementById("nav").classList.remove("is-compact"),
});

/* ---------- hero: the student's desk — sticky-note chaos assembles, then the
   camera dives into the laptop (where the clean route lives) and floods blue ---------- */
{
  /* The vanishing point is the CENTRE OF THE LAPTOP SCREEN, measured rather
     than guessed. At high scale a 2% error throws the target a third of a
     viewport off, which is what made the old dive drift. Measure unscaled or
     the percentage is computed against the wrong box. */
  const stage = document.querySelector(".desk-stage");
  const setOrigin = () => {
    const prev = gsap.getProperty(stage, "scale") || 1;
    gsap.set(stage, { scale: 1 });
    const s = stage.getBoundingClientRect();
    const c = document.querySelector(".laptop-screen").getBoundingClientRect();
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
      end: "+=380%",
      scrub: 1,
      pin: true,
      anticipatePin: 1,
      invalidateOnRefresh: true,
      // will-change is a lease, not a permanent promotion
      onToggle: (self) => document.documentElement.classList.toggle("is-diving", self.isActive),
    },
  });

  // intro plays once on load (not scroll-tied) so the desk is alive at first paint
  const introTl = gsap.timeline({ delay: 0.2 })
    .from(".softboard", { y: -26, opacity: 0, duration: 0.5, ease: "power2.out" }, 0)
    .from(".board-sheet", { y: -34, opacity: 0, duration: 0.5, ease: "back.out(1.7)" }, 0.2)
    .from(".sticky", { y: -30, opacity: 0, scale: 0.6, stagger: 0.055, duration: 0.4, ease: "back.out(2)" }, 0.35)
    .from(".board-polaroid", { scale: 0, rotation: -14, duration: 0.45, ease: "back.out(2)" }, 0.8)
    .from(".laptop", { y: 46, opacity: 0, duration: 0.55, ease: "power2.out" }, 0.45)
    .from(".desk-prop", { y: 40, opacity: 0, stagger: 0.12, duration: 0.5, ease: "back.out(1.6)" }, 0.65)
    .from(".app-msg, .app-chips, .app-input", { opacity: 0, y: 6, stagger: 0.14, duration: 0.35 }, 1.0);

  // the scrubbed part: notes scatter past the camera, dive into the screen, flood blue
  tl.to(".sticky", {
      x: (i) => (i % 2 ? 1 : -1) * (160 + (i * 67) % 300),
      y: (i) => -140 - (i * 53) % 260,
      rotation: (i) => (i % 2 ? 1 : -1) * (24 + (i * 11) % 40),
      opacity: 0,
      stagger: 0.05,
      duration: 1.1,
      ease: "power2.in",
    }, 0.15)
    .to(".board-sheet, .board-polaroid", { y: -110, opacity: 0, duration: 0.7, ease: "power2.in" }, 0.75)
    .to(".scroll-hint", { opacity: 0, duration: 0.4 }, 1.0);

  /* THE DIVE, in the log domain.
     Perceived zoom speed is (ds/dt)/s, not ds/dt — so easing raw scale reads
     "abrupt, then floaty", which is exactly what scale:15 + power2.in did.
     Ease the EXPONENT instead and the camera holds a constant apparent speed
     with a gentle build and a gentle arrival. Layers take different targets,
     which is what gives the props parallax as they pass. */
  const cam = { t: 0 };
  const ez = gsap.parseEase("power1.inOut");
  const layers = [
    [document.querySelector(".softboard"), 2.3],   // furthest back, slowest
    [stage, 6.0],
    [document.querySelector(".desk-band"), 3.1],
    [gsap.utils.toArray(".desk-prop"), 4.4],       // nearest, fastest
  ];
  tl.to(cam, {
    t: 1, ease: "none", duration: 2.4,
    onUpdate() {
      const e = ez(cam.t);
      layers.forEach(([el, S]) => gsap.set(el, { scale: Math.pow(S, e) }));
    },
  }, 0.4);

  /* The handoff: the laptop's interface at real size, on the same near-white
     the screen already is. Both rects coincident and both still moving, so it
     reads as focus resolving rather than a swap. No flat colour card. */
  tl.fromTo("#plate", { autoAlpha: 0, scale: 0.94 },
                      { autoAlpha: 1, scale: 1, ease: "power2.out", duration: 0.5 }, 2.3);
  tl.to(".desk-stage", { autoAlpha: 0, duration: 0.3 }, 2.55);

  /* The screen has to EARN the dive, so it plays a real exchange rather than
     sitting empty: the student types, sends, and ACE answers with a plan. */
  const thread = ["#pmsgMe", "#pmsgBot", "#pplan", "#pchips"];
  gsap.set(thread, { autoAlpha: 0 });

  // the student asks — steps(), never a per-character chatbot typer
  const question = "Can I graduate by Spring 2027?";
  const typed = { n: 0 };
  tl.to(typed, {
    n: question.length, ease: "steps(" + question.length + ")", duration: 0.65,
    onUpdate() { document.getElementById("typedQuestion").textContent = question.slice(0, Math.round(typed.n)); },
  }, 2.6);

  // it sends: the input empties and the question becomes the first message
  tl.add(() => { document.getElementById("typedQuestion").textContent = ""; }, 3.35);
  tl.fromTo("#pmsgMe", { autoAlpha: 0, y: 10 },
                       { autoAlpha: 1, y: 0, ease: "power2.out", duration: 0.3 }, 3.35);
  // ACE answers, then the plan and the verdict land in sequence
  tl.fromTo("#pmsgBot", { autoAlpha: 0, y: 12 },
                        { autoAlpha: 1, y: 0, ease: "power2.out", duration: 0.4 }, 3.7);
  tl.fromTo("#pplan",   { autoAlpha: 0, y: 8 },
                        { autoAlpha: 1, y: 0, ease: "power2.out", duration: 0.35 }, 4.05);
  tl.fromTo("#pchips",  { autoAlpha: 0, y: 6 },
                        { autoAlpha: 1, y: 0, ease: "power2.out", duration: 0.3 }, 4.35);
  tl.to({}, { duration: 0.55 }, 4.65);          // read it before we move on
  tl.to("#plate", { autoAlpha: 0, duration: 0.4 }, 5.3);

  tl
    // Meet ACE — she settles up into frame
    .to(".scene-meet", { autoAlpha: 1, duration: 0.6 }, 5.55)
    .fromTo(".scene-meet .profile",
      { yPercent: 14, opacity: 0 },
      { yPercent: 0, opacity: 1, ease: "power2.out", duration: 1.2 }, 5.55)
    .fromTo(".meet-line", { yPercent: 30, opacity: 0 }, { yPercent: 0, opacity: 1, duration: 1 }, 6.05)
    .to(".scene-meet", { autoAlpha: 0, duration: 0.5 }, 7.4)

    .to(".scene-tagline", { autoAlpha: 1, duration: 0.5 }, 7.7)
    .fromTo(".scene-tagline h2", { scale: 0.9 }, { scale: 1, duration: 1.2 }, 7.7)
    .to({}, { duration: 0.6 }); // hold before unpin

  /* Embedded panes sometimes lay the page out at 0x0 and stall the rAF ticker,
     which freezes the intro at opacity 0 and caches garbage tween values.
     When the viewport becomes real: finish the intro instantly, make every
     tween re-read its start values, and re-measure all the pins. */
  let zeroLayout = window.innerHeight < 100;
  window.addEventListener("resize", () => {
    if (window.innerHeight < 100) { zeroLayout = true; return; }
    if (!zeroLayout) return;
    zeroLayout = false;
    introTl.progress(1);
    gsap.globalTimeline.getChildren(true, true, true).forEach((t) => t.invalidate());
    ScrollTrigger.refresh();
    window.scrollTo(0, 0);
  });
}

/* ---------- statement: pin + line reveals + word rotator ---------- */
{
  const words = gsap.utils.toArray(".rot-word");
  const tl = gsap.timeline({
    scrollTrigger: {
      trigger: ".statement",
      start: "top top",
      end: "+=250%",
      scrub: 1,
      pin: true,
    },
  });

  tl.from(".statement-h .line", { yPercent: 120, opacity: 0, stagger: 0.4, duration: 1 })
    .from(".statement-sub p:first-child", { opacity: 0, y: 40, duration: 0.8 });
  // step through however many rotating phrases exist
  for (let i = 1; i < words.length; i++) {
    tl.to(words[i - 1], { yPercent: -110, duration: 0.5 }, "+=0.7")
      .fromTo(words[i], { yPercent: 110 }, { yPercent: 0, duration: 0.5 }, "<");
  }
  tl.from(".statement-kicker", { opacity: 0, y: 40, duration: 0.8 }, "+=0.4")
    .to({}, { duration: 0.5 });
}

/* ---------- show: draw the three arrows ---------- */
gsap.to(".arrow path", {
  strokeDashoffset: 0,
  stagger: 0.25,
  ease: "none",
  scrollTrigger: { trigger: ".show", start: "top 70%", end: "bottom 60%", scrub: 1 },
});

/* ---------- steps: cards stack via CSS sticky; add a settle-in per card ---------- */
gsap.utils.toArray(".step-card").forEach((card) => {
  gsap.from(card.querySelector(".step-body"), {
    y: 60,
    scrollTrigger: { trigger: card, start: "top 90%", end: "top 40%", scrub: 1 },
  });
});

/* ---------- bgwork: notifications pop in ---------- */
{
  const tl = gsap.timeline({
    scrollTrigger: { trigger: ".bgwork", start: "top 55%", end: "bottom bottom", scrub: 1 },
  });
  tl.from(".monitor", { y: 120, duration: 1 })
    .from(".maggie-desk-img", { y: 160, duration: 1 }, 0.2)
    .to(".notif-1", { opacity: 1, y: 0, scale: 1, duration: 0.6 }, 0.9)
    .to(".notif-2", { opacity: 1, y: 0, scale: 1, duration: 0.6 }, 1.4)
    .to(".notif-3", { opacity: 1, y: 0, scale: 1, duration: 0.6 }, 1.9);
}

/* ---------- different: pin; 3 phases swap dome / labels / callout ---------- */
{
  const phases = [
    { dome: ".dome-pink", labels: ".labels-1", callout: ".co-1" },
    { dome: ".dome-amber", labels: ".labels-2", callout: ".co-2" },
    { dome: ".dome-purple", labels: ".labels-3", callout: ".co-3" },
  ];

  const tl = gsap.timeline({
    scrollTrigger: {
      trigger: ".different",
      start: "top top",
      end: "+=300%",
      scrub: 1,
      pin: true,
    },
  });

  tl.from(".head-stage", { y: 200, duration: 1 }, 0)
    .from(".different .tape", { x: -80, opacity: 0, stagger: 0.2, duration: 0.7 }, 0)
    .from(".callout", { opacity: 0, duration: 0.6 }, 0.4);

  // labels of phase 1 pop in
  tl.fromTo(".labels-1 .label",
    { scale: 0, opacity: 0 },
    { scale: 1, opacity: 1, stagger: 0.08, duration: 0.5 }, 0.8);

  phases.forEach((p, i) => {
    if (i === 0) return;
    const prev = phases[i - 1];
    const at = 1.6 + (i - 1) * 2.2;
    tl.to(prev.dome, { opacity: 0, duration: 0.6 }, at)
      .to(p.dome, { opacity: 1, duration: 0.6 }, at)
      .to(prev.labels + " .label", { scale: 0, opacity: 0, stagger: 0.04, duration: 0.3 }, at)
      .add(() => {
        document.querySelectorAll(".labels").forEach(l => l.classList.remove("is-active"));
        document.querySelector(p.labels).classList.add("is-active");
        document.querySelectorAll(".callout-line").forEach(c => c.classList.remove("is-active"));
        document.querySelector(p.callout).classList.add("is-active");
      }, at + 0.3)
      .fromTo(p.labels + " .label",
        { scale: 0, opacity: 0 },
        { scale: 1, opacity: 1, stagger: 0.06, duration: 0.4 }, at + 0.4);
  });
  tl.to({}, { duration: 0.6 });

  // make label-set/callout swaps reversible when scrolling back up
  ScrollTrigger.create({
    trigger: ".different",
    start: "top top",
    end: "+=300%",
    scrub: true,
    onUpdate(self) {
      const seg = Math.min(2, Math.floor(self.progress * 3));
      document.querySelectorAll(".labels").forEach((l, i) => l.classList.toggle("is-active", i === seg));
      document.querySelectorAll(".callout-line").forEach((c, i) => c.classList.toggle("is-active", i === seg));
    },
  });
}

/* ---------- pricing cards rise in (stickers drop with gravity, below) ---------- */
gsap.utils.toArray(".tier, .included, .enterprise").forEach((el) => {
  gsap.from(el, {
    y: 70,
    opacity: 0,
    duration: 0.8,
    scrollTrigger: { trigger: el, start: "top 88%" },
  });
});

/* ---------- tape titles wobble in ---------- */
gsap.utils.toArray(".pricing .tape, .testimonials .tape, .final .tape").forEach((el, i) => {
  gsap.from(el, {
    x: -70,
    opacity: 0,
    duration: 0.7,
    delay: (i % 2) * 0.12,
    scrollTrigger: { trigger: el, start: "top 90%" },
  });
});

/* ---------- built-by stickers: drop in with gravity + bounce ---------- */
gsap.utils.toArray(".starburst").forEach((el, i) => {
  gsap.from(el, {
    y: -420,
    rotation: (i % 2 ? 1 : -1) * (18 + i * 7),
    ease: "bounce.out",
    duration: 1.1,
    delay: i * 0.12,
    scrollTrigger: { trigger: ".stickers", start: "top 80%" },
  });
});

/* ---------- waitlist: same contract as the previous landing —
   POST {email, referral} to /waitlist, render the "you're #N" reply ---------- */
{
  const API = window.ACE_API_URL || "https://web-production-7ffe.up.railway.app";
  const form = document.getElementById("waitlistForm");
  const input = document.getElementById("wlEmail");
  const submit = document.getElementById("wlSubmit");
  const errEl = document.getElementById("wlError");
  const doneEl = document.getElementById("wlDone");

  const fail = (msg) => {
    errEl.textContent = msg;
    errEl.hidden = false;
    submit.disabled = false;
    submit.textContent = "Join the waitlist";
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = input.value.trim();
    errEl.hidden = true;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      fail("That email doesn't look right — mind checking it?");
      return;
    }
    submit.disabled = true;
    submit.textContent = "Joining…";
    try {
      const referral = new URLSearchParams(location.search).get("ref") || "landing";
      const res = await fetch(`${API}/waitlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, referral }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || "Something went wrong.");

      const n = data.position;
      doneEl.innerHTML = data.already
        ? `✓ Already on the list — you're <strong>#${n}</strong>. We'll be in touch.`
        : `✓ You're in — <strong>#${n}</strong> on the list.` +
          (n <= 100 ? " Early-access group. 🎉" : " We'll email you when your spot opens.");
      form.hidden = true;
      doneEl.hidden = false;
      gsap.from(doneEl, { scale: 0.9, opacity: 0, duration: 0.4, ease: "back.out(2)" });
    } catch (err) {
      fail(err.message || "Something went wrong — try again.");
    }
  });
}

/* ---------- final: head rises, doodles pop ---------- */
{
  const tl = gsap.timeline({
    scrollTrigger: { trigger: ".final", start: "top 60%", end: "bottom bottom", scrub: 1 },
  });
  tl.from(".final-head", { yPercent: 90, duration: 1.4 })
    .from(".doodle-arrow path", { strokeDashoffset: 400, strokeDasharray: 400, duration: 1 }, 0.4)
    .from(".doodle-spark, .doodle-hash", { scale: 0, opacity: 0, stagger: 0.2, duration: 0.5 }, 0.7);
}
