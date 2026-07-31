/* ============================================================================
   ace. landing — "still awake." · Phase 1 choreography.

   Motion rules (brand/BRAND.md): one ease for ~80% of motion; exits pinned at
   ~120ms; nothing loops idle; the emerald marks closure only. The clock is a
   real readout and doubles as the page's scroll axis. All patterns here are
   our own GSAP/CSS implementations.
   ============================================================================ */
gsap.registerPlugin(ScrollTrigger);
ScrollTrigger.config({ ignoreMobileResize: true });

/* the one curve — cubic-bezier(.165,.84,.44,1) from tokens */
const EASE = gsap.parseEase("0.165,0.84,0.44,1");
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

const q = (s) => document.querySelector(s);

/* ---------------------------------------------------------------------------
   the clock · a real readout that scrubs with scroll.
   02:12 -> 02:14 during the intro, then 02:14 -> 02:20 across the pile.
   --------------------------------------------------------------------------- */
const clockEl = q("#clock");
const setClock = (h, m) => {
  if (clockEl) clockEl.textContent =
    String(h).padStart(2, "0") + ":" + String(Math.round(m)).padStart(2, "0");
};

/* ---------------------------------------------------------------------------
   ch.1 · hero intro — plays once. letters land a, c, e; the dot lands last.
   --------------------------------------------------------------------------- */
if (!reduced) {
  const intro = gsap.timeline({ delay: 0.25, defaults: { ease: EASE } });
  intro
    .add(() => setClock(2, 12), 0)
    .to(".g-a", { opacity: 1, y: 0, duration: 0.34 }, 0.10)
    .add(() => setClock(2, 13), 0.32)
    .to(".g-c", { opacity: 1, y: 0, duration: 0.34 }, 0.34)
    .to(".g-e", { opacity: 1, y: 0, duration: 0.34 }, 0.58)
    .add(() => setClock(2, 14), 0.62)
    /* the dot drops onto the baseline — the view's single emerald, landing last */
    .to(".g-dot", { opacity: 1, duration: 0.06 }, 0.98)
    .to(".g-dot", { y: 0, duration: 0.42 }, 0.98)
    .to(".hero-line", { opacity: 1, y: 0, duration: 0.4 }, 1.42)
    .to(".hero-hint", { opacity: 1, duration: 0.3 }, 1.75);
} else {
  setClock(2, 14);
}

/* ---------------------------------------------------------------------------
   ch.2 · the pile — everything a student is carrying drops and settles.
   Deterministic: positions are packed first (shelf-pack from the floor up),
   then each word falls into its precomputed slot. Plays once on entry.
   --------------------------------------------------------------------------- */
{
  const pile = q("#pile");
  const words = Array.from(pile.children);

  /* seeded PRNG so every visitor sees the same pile (and QA is reproducible) */
  let seed = 20260214;
  const rand = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;

  const layout = () => {
    const W = pile.clientWidth;
    const H = pile.clientHeight;
    /* size + tone first (affects measurement). A few carry weight at the
       28px cap; the rest scatter down to 15px. Every 4th word is ghost —
       the ones you're ignoring. */
    words.forEach((w, i) => {
      const big = i % 5 === 0;
      const size = big ? 27 : 15 + Math.round(rand() * 9);
      w.style.fontSize = size + "px";
      w.style.color = i % 4 === 3 ? "var(--ace-ghost)" : "var(--ace-ink)";
      w.dataset.rot = ((rand() * 22) - 11).toFixed(1);
    });
    /* shelf-pack rows from the floor up with jitter — reads as a heap,
       stays deterministic, never overlaps text into unreadability */
    let y = 6;                                  // px above the pile floor
    let x = 8 + rand() * 30;
    let rowH = 0;
    words.forEach((w) => {
      const ww = w.offsetWidth, wh = w.offsetHeight;
      if (x + ww > W - 8) { x = 8 + rand() * 30; y += rowH * 0.82; rowH = 0; }
      const fx = x, fy = H - y - wh;
      x += ww + 10 + rand() * 26;
      rowH = Math.max(rowH, wh + 4);
      w.dataset.fx = Math.round(fx);
      w.dataset.fy = Math.round(fy);
    });
  };
  layout();

  if (reduced) {
    words.forEach((w) => {
      gsap.set(w, { x: +w.dataset.fx, y: +w.dataset.fy, rotation: +w.dataset.rot, opacity: 1 });
    });
  } else {
    /* park every word above the frame in its column, then drop on entry */
    words.forEach((w) => {
      gsap.set(w, {
        x: +w.dataset.fx,
        y: -140 - Math.random() * 260,
        rotation: +w.dataset.rot * 2.4,
        opacity: 1,
      });
    });
    ScrollTrigger.create({
      trigger: "#night",
      start: "top 62%",
      once: true,
      onEnter: () => {
        const tl = gsap.timeline();
        words.forEach((w, i) => {
          tl.to(w, {
            y: +w.dataset.fy,
            rotation: +w.dataset.rot,
            duration: 0.6 + Math.random() * 0.3,
            ease: EASE,
          }, i * 0.035);
        });
      },
    });
    /* re-pack on real resizes only (not iOS URL-bar churn) */
    let rt;
    window.addEventListener("resize", () => {
      clearTimeout(rt);
      rt = setTimeout(() => {
        layout();
        words.forEach((w) => gsap.set(w, {
          x: +w.dataset.fx, y: +w.dataset.fy, rotation: +w.dataset.rot,
        }));
      }, 180);
    });
  }

  /* the clock scrubs 02:14 -> 02:20 across the night section */
  ScrollTrigger.create({
    trigger: "#night",
    start: "top 80%",
    end: "bottom 40%",
    onUpdate: (self) => setClock(2, 14 + self.progress * 6),
  });
}

/* ---------------------------------------------------------------------------
   the pixel-dissolve menu — hard-edged ink cells stagger in randomly, cover,
   then the panel appears. One pass, ~500ms in, ~350ms out. Reduced motion
   gets a plain fade. Cells are ~56px so no flash-risk fine grids.
   --------------------------------------------------------------------------- */
{
  const menu = q("#menu");
  const grid = q("#menuGrid");
  const panel = q(".menu-panel");
  const btn = q("#menuBtn");
  const closeBtn = q("#menuClose");
  let cells = [];
  let open = false;
  let busy = false;

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
    busy = true;
    open = to;
    btn.setAttribute("aria-expanded", String(to));
    if (to) {
      menu.hidden = false;
      buildGrid();
      if (reduced) {
        gsap.set(cells, { opacity: 1 });
        gsap.set(panel, { autoAlpha: 1 });
        busy = false;
        closeBtn.focus();
      } else {
        const tl = gsap.timeline({ onComplete: () => { busy = false; closeBtn.focus(); } });
        /* hard cells: no fade per cell — a raster wipe, not a dissolve-blur */
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
  /* in-page anchors close the menu, then the browser jumps */
  menu.querySelectorAll('a[href^="#"]').forEach((a) =>
    a.addEventListener("click", () => setOpen(false)));
}

/* ---------------------------------------------------------------------------
   waitlist — unchanged contract: POST {email, referral} -> {position, already}.
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
    btn.textContent = "join the waitlist";
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
