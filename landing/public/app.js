/* ============================================================================
   ace. landing — "still awake." · full choreography.

   Motion rules (brand/BRAND.md): one ease for ~80% of motion; exits pinned at
   ~120ms; nothing loops idle; the emerald marks closure only. The mono clock
   is a real readout and the page's scroll axis: 02:12 at load, 07:00 at the
   end. Text reveals are one-shots — never scrubbed. All patterns here are
   our own GSAP/CSS implementations.
   ============================================================================ */
gsap.registerPlugin(ScrollTrigger);
ScrollTrigger.config({ ignoreMobileResize: true });

/* the one curve — cubic-bezier(.165,.84,.44,1) from tokens */
const EASE = gsap.parseEase("0.165,0.84,0.44,1");
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const q = (s) => document.querySelector(s);
const qa = (s) => gsap.utils.toArray(s);

/* ---------------------------------------------------------------------------
   the clock
   --------------------------------------------------------------------------- */
const clockEl = q("#clock");
const setClockMin = (total) => {
  const h = Math.floor(total / 60) % 24;
  const m = Math.floor(total % 60);
  if (clockEl) clockEl.textContent =
    String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0");
};
const T = (h, m) => h * 60 + m;

/* a section stamps the clock when it enters; leaving backwards restores the
   previous stamp, so the readout always agrees with what's on screen */
const stampClock = (trigger, start, mins, prevMins) => {
  ScrollTrigger.create({
    trigger, start,
    onEnter: () => setClockMin(mins),
    onLeaveBack: () => setClockMin(prevMins),
  });
};

/* ---------------------------------------------------------------------------
   02:14 · hero intro — plays once. letters land; the dot lands last.
   --------------------------------------------------------------------------- */
if (!reduced) {
  const intro = gsap.timeline({ delay: 0.25, defaults: { ease: EASE } });
  intro
    .add(() => setClockMin(T(2, 12)), 0)
    .to(".g-a", { opacity: 1, y: 0, duration: 0.34 }, 0.10)
    .add(() => setClockMin(T(2, 13)), 0.32)
    .to(".g-c", { opacity: 1, y: 0, duration: 0.34 }, 0.34)
    .to(".g-e", { opacity: 1, y: 0, duration: 0.34 }, 0.58)
    .add(() => setClockMin(T(2, 14)), 0.62)
    .to(".g-dot", { opacity: 1, duration: 0.06 }, 0.98)
    .to(".g-dot", { y: 0, duration: 0.42 }, 0.98)
    .to(".hero-line", { opacity: 1, y: 0, duration: 0.4 }, 1.42)
    .to(".hero-hint", { opacity: 1, duration: 0.3 }, 1.75);
} else {
  setClockMin(T(2, 14));
}

/* ---------------------------------------------------------------------------
   02:14 → 02:20 · the pile — deterministic heap, plays once on entry.
   --------------------------------------------------------------------------- */
{
  const pile = q("#pile");
  const words = Array.from(pile.children);

  /* seeded PRNG: every visitor sees the same pile; QA is reproducible */
  let seed = 20260214;
  const rand = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;

  const layout = () => {
    seed = 20260214;
    const W = pile.clientWidth, H = pile.clientHeight;
    words.forEach((w, i) => {
      const big = i % 5 === 0;
      const size = big ? 27 : 15 + Math.round(rand() * 9);
      w.style.fontSize = size + "px";
      w.style.color = i % 4 === 3 ? "var(--ace-ghost)" : "var(--ace-ink)";
      w.dataset.rot = ((rand() * 22) - 11).toFixed(1);
    });
    let y = 6, x = 8 + rand() * 30, rowH = 0;
    words.forEach((w) => {
      const ww = w.offsetWidth, wh = w.offsetHeight;
      if (x + ww > W - 8) { x = 8 + rand() * 30; y += rowH * 0.82; rowH = 0; }
      w.dataset.fx = Math.round(x);
      w.dataset.fy = Math.round(H - y - wh);
      x += ww + 10 + rand() * 26;
      rowH = Math.max(rowH, wh + 4);
    });
  };
  layout();

  if (reduced) {
    words.forEach((w) => gsap.set(w, {
      x: +w.dataset.fx, y: +w.dataset.fy, rotation: +w.dataset.rot, opacity: 1,
    }));
  } else {
    words.forEach((w) => gsap.set(w, {
      x: +w.dataset.fx,
      y: -140 - Math.random() * 260,
      rotation: +w.dataset.rot * 2.4,
      opacity: 1,
    }));
    ScrollTrigger.create({
      trigger: "#night", start: "top 62%", once: true,
      onEnter: () => {
        const tl = gsap.timeline();
        words.forEach((w, i) => {
          tl.to(w, {
            y: +w.dataset.fy, rotation: +w.dataset.rot,
            duration: 0.6 + Math.random() * 0.3, ease: EASE,
          }, i * 0.035);
        });
      },
    });
    let rt;
    addEventListener("resize", () => {
      clearTimeout(rt);
      rt = setTimeout(() => {
        layout();
        words.forEach((w) => gsap.set(w, {
          x: +w.dataset.fx, y: +w.dataset.fy, rotation: +w.dataset.rot,
        }));
      }, 180);
    });
  }

  /* the clock scrubs 02:14 → 02:20 across the night */
  ScrollTrigger.create({
    trigger: "#night", start: "top 80%", end: "bottom 40%",
    onUpdate: (self) => setClockMin(T(2, 14) + self.progress * 6),
  });
}

/* ---------------------------------------------------------------------------
   02:22 · the ask — the question types, the verdict lands, the emerald
   period is performed. One-shot; text is never scrubbed.
   --------------------------------------------------------------------------- */
{
  const QUESTION = "can i still graduate by spring '27 if i failed MATH 230?";
  const typedEl = q("#askTyped");
  const caret = q("#askCaret");

  if (reduced) {
    typedEl.textContent = QUESTION;
    caret.style.display = "none";
  } else {
    const typed = { n: 0 };
    ScrollTrigger.create({
      trigger: "#ask", start: "top 60%", once: true,
      onEnter: () => {
        const tl = gsap.timeline({ defaults: { ease: EASE } });
        tl.to(typed, {
          n: QUESTION.length,
          ease: "steps(" + QUESTION.length + ")",
          duration: 1.15,
          onUpdate() { typedEl.textContent = QUESTION.slice(0, Math.round(typed.n)); },
        })
          .add(() => { caret.style.display = "none"; }, "+=0.25")
          .to(".ask-verdict", { opacity: 1, y: 0, duration: 0.34 }, "+=0.05")
          .to(".ask-body",    { opacity: 1, y: 0, duration: 0.4 }, "+=0.18")
          .to(".ask-receipt", { opacity: 1, y: 0, duration: 0.4 }, "+=0.12");
      },
    });
  }
  stampClock("#ask", "top 60%", T(2, 22), T(2, 20));
}

/* ---------------------------------------------------------------------------
   02:23 → 02:27 · the folder — the kept sticky-stack mechanic, restyled.
   Cards enter once; each stamps the clock with its own minute.
   --------------------------------------------------------------------------- */
qa(".step").forEach((step, i) => {
  const [h, m] = step.dataset.time.split(":").map(Number);
  if (!reduced) {
    gsap.set(step.querySelector(".step-body"), { opacity: 0, y: 40 });
    ScrollTrigger.create({
      trigger: step, start: "top 78%", once: true,
      onEnter: () => gsap.to(step.querySelector(".step-body"),
        { opacity: 1, y: 0, duration: 0.55, ease: EASE }),
    });
  }
  stampClock(step, "top 55%", T(h, m), i === 0 ? T(2, 22) : T(h, m - 2));
});

/* ---------------------------------------------------------------------------
   02:31 → 03:05 · the rest of the night — three registers, three receipts.
   --------------------------------------------------------------------------- */
qa(".qa").forEach((row, i) => {
  const [h, m] = row.dataset.time.split(":").map(Number);
  const parts = row.querySelectorAll(".qa-q, .qa-a, .qa-receipt");
  if (!reduced) {
    ScrollTrigger.create({
      trigger: row, start: "top 72%", once: true,
      onEnter: () => gsap.to(parts,
        { opacity: 1, y: 0, duration: 0.45, ease: EASE, stagger: 0.16 }),
    });
  }
  const prev = i === 0 ? T(2, 27) : T(...qa(".qa")[i - 1].dataset.time.split(":").map(Number));
  stampClock(row, "top 65%", T(h, m), prev);
});

/* ---------------------------------------------------------------------------
   03:11 · the receipt — the card assembles, the ink route draws through the
   nodes, the emerald dot lands on the destination. The route is never broken.
   --------------------------------------------------------------------------- */
{
  const ink = q("#routeInk");
  const dot = q("#routeDot");
  const len = ink.getTotalLength();

  if (reduced) {
    gsap.set([".receipt-card", ".receipt-line"], { opacity: 1, y: 0 });
  } else {
    gsap.set(ink, { strokeDasharray: len, strokeDashoffset: len });
    gsap.set(dot, { scale: 0, transformOrigin: "center" });
    ScrollTrigger.create({
      trigger: "#receipt", start: "top 62%", once: true,
      onEnter: () => {
        const tl = gsap.timeline({ defaults: { ease: EASE } });
        tl.to(".receipt-card", { opacity: 1, y: 0, duration: 0.5 })
          .to(ink, { strokeDashoffset: 0, duration: 0.9, ease: "none" }, "+=0.1")
          .to(dot, { scale: 1, duration: 0.25 })
          .to(".receipt-line", { opacity: 1, y: 0, duration: 0.45 }, "+=0.1");
      },
    });
  }
  stampClock("#receipt", "top 62%", T(3, 11), T(3, 5));
}

/* ---------------------------------------------------------------------------
   03:11 → 07:00 · morning — the student finally sleeps. The clock does the
   telling: it scrubs through the missing hours as the page empties out.
   --------------------------------------------------------------------------- */
ScrollTrigger.create({
  trigger: "#join", start: "top 80%", end: "top 10%",
  onUpdate: (self) => setClockMin(T(3, 11) + self.progress * (T(7, 0) - T(3, 11))),
});

/* ---------------------------------------------------------------------------
   the pixel-dissolve menu — hard cells raster-wipe, one pass. ~56px blocks.
   --------------------------------------------------------------------------- */
{
  const menu = q("#menu");
  const grid = q("#menuGrid");
  const panel = q(".menu-panel");
  const btn = q("#menuBtn");
  const closeBtn = q("#menuClose");
  let cells = [], open = false, busy = false;

  const buildGrid = () => {
    const cx = Math.ceil(innerWidth / 56);
    const cy = Math.ceil(innerHeight / 56);
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
        gsap.set(cells, { opacity: 1 });
        gsap.set(panel, { autoAlpha: 1 });
        busy = false; closeBtn.focus();
      } else {
        const tl = gsap.timeline({ onComplete: () => { busy = false; closeBtn.focus(); } });
        tl.to(cells, { opacity: 1, duration: 0.01, stagger: { amount: 0.42, from: "random" } })
          .to(panel, { autoAlpha: 1, duration: 0.18, ease: EASE }, 0.46);
      }
    } else {
      const done = () => { menu.hidden = true; busy = false; btn.focus(); };
      if (reduced) {
        gsap.set(panel, { autoAlpha: 0 });
        gsap.set(cells, { opacity: 0 });
        done();
      } else {
        const tl = gsap.timeline({ onComplete: done });
        tl.to(panel, { autoAlpha: 0, duration: 0.12, ease: EASE })
          .to(cells, { opacity: 0, duration: 0.01, stagger: { amount: 0.3, from: "random" } }, 0.08);
      }
    }
  };

  btn.addEventListener("click", () => setOpen(true));
  closeBtn.addEventListener("click", () => setOpen(false));
  addEventListener("keydown", (e) => { if (e.key === "Escape" && open) setOpen(false); });
  menu.querySelectorAll('a[href^="#"]').forEach((a) =>
    a.addEventListener("click", () => setOpen(false)));
}

/* ---------------------------------------------------------------------------
   waitlist — unchanged contract: POST {email, referral} → {position, already}.
   The emerald period appears only on the resolved state.
   --------------------------------------------------------------------------- */
{
  const API = window.ACE_API_URL || "https://web-production-7ffe.up.railway.app";
  const form = q("#waitlistForm");
  const input = q("#wlEmail");
  const btn = q("#wlSubmit");
  const errEl = q("#wlError");
  const okEl = q("#wlDone");

  const fail = (msg) => {
    errEl.textContent = msg;
    errEl.hidden = false;
    btn.disabled = false;
    btn.textContent = "join the first 100";
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = input.value.trim();
    errEl.hidden = true;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      fail("that email doesn't look right — mind checking it");
      return;
    }
    btn.disabled = true;
    btn.textContent = "joining…";
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
      const inFirst100 = data.position <= 100;
      okEl.innerHTML = data.already
        ? `already on the list — you're #${n}<span class="period">.</span>`
        : inFirst100
          ? `you're in — #${n} of the first 100<span class="period">.</span>`
          : `you're in — #${n} on the list<span class="period">.</span>`;
      form.hidden = true;
      okEl.hidden = false;
    } catch (err) {
      fail((err.message || "something went wrong — try again.").toLowerCase());
    }
  });
}
