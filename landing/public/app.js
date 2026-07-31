/* ============================================================================
   ace. landing — Apple-grammar choreography.

   Motion serves the artifact, never the mood. Each slab's card assembles once
   on entry; nothing scrubs text, nothing loops idle. One ease curve
   (cubic-bezier(.165,.84,.44,1)); exits pinned ~120ms.
   ============================================================================ */
gsap.registerPlugin(ScrollTrigger);
ScrollTrigger.config({ ignoreMobileResize: true });

const EASE = gsap.parseEase("0.165,0.84,0.44,1");
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const q = (s) => document.querySelector(s);
const qa = (s) => gsap.utils.toArray(s);

/* ---------------------------------------------------------------------------
   hero — the letters land, the dot lands last. plays once.
   --------------------------------------------------------------------------- */
if (!reduced) {
  gsap.timeline({ delay: 0.25, defaults: { ease: EASE } })
    .to(".g-a", { opacity: 1, y: 0, duration: 0.34 }, 0.10)
    .to(".g-c", { opacity: 1, y: 0, duration: 0.34 }, 0.34)
    .to(".g-e", { opacity: 1, y: 0, duration: 0.34 }, 0.58)
    .to(".g-dot", { opacity: 1, duration: 0.06 }, 0.98)
    .to(".g-dot", { y: 0, duration: 0.42 }, 0.98)
    .to(".hero-line", { opacity: 1, y: 0, duration: 0.4 }, 1.42)
    .to(".hero-sub", { opacity: 1, duration: 0.4 }, 1.62)
    .to(".hero-hint", { opacity: 1, duration: 0.3 }, 1.85);
}

/* ---------------------------------------------------------------------------
   the twelve-page pdf — grey lines, generated so the density reads as a real
   document rather than a placeholder. Deterministic widths.
   --------------------------------------------------------------------------- */
{
  const host = q("#docLines");
  let seed = 749;
  const rand = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
  const frag = document.createDocumentFragment();
  for (let i = 0; i < 16; i++) {
    const line = document.createElement("i");
    line.style.width = (36 + rand() * 62).toFixed(0) + "%";
    frag.appendChild(line);
  }
  host.appendChild(frag);
}

/* ---------------------------------------------------------------------------
   the slab module. Enter 560ms, exit 140ms (4:1) — symmetric timing is why
   most motion reads cheap. Stagger by mass: rows ~45ms, cards ~90ms.
   --------------------------------------------------------------------------- */
/* The bar reads the ground beneath it. This is legibility, not motion — an ink
   mark on an ink slab is invisible — so it runs even under reduced-motion. */
const bar = q(".bar");
qa(".on-ink, .payoff, .foot").forEach((dark) => {
  ScrollTrigger.create({
    trigger: dark, start: "top 60px", end: "bottom 60px",
    onToggle: (self) => bar.classList.toggle("is-inverted", self.isActive),
  });
});

if (!reduced) {
  qa(".slab").forEach((slab) => {
    const head = slab.querySelector(".slab-head");
    const art = slab.querySelector(".card, .index");
    const inner = slab.querySelectorAll(".rows p, .ac-plan p, .index li, .doc-lines i");

    gsap.set(head, { opacity: 0, y: 20 });
    gsap.set(art, { opacity: 0, y: 30 });
    if (inner.length) gsap.set(inner, { opacity: 0 });

    ScrollTrigger.create({
      trigger: slab, start: "top 72%", once: true,
      onEnter: () => {
        gsap.timeline({ defaults: { ease: EASE, duration: 0.56 } })
          .to(head, { opacity: 1, y: 0 })
          .to(art, { opacity: 1, y: 0 }, "-=0.30")
          .to(inner, { opacity: 1, duration: 0.34, stagger: 0.045 }, "-=0.26");
      },
    });

    /* SCRUB — compositor-only (transform), artifact layers only. Layout and
       text never scrub; that is what produces the motion-sick imitation. */
    if (art) {
      gsap.fromTo(art, { yPercent: 4 }, {
        yPercent: -4, ease: "none",
        scrollTrigger: { trigger: slab, start: "top bottom", end: "bottom top", scrub: 0.6 },
      });
    }
  });

  /* the hero recedes as you leave it — the page has depth, not just sections */
  gsap.to(".wordmark", {
    scale: 0.86, opacity: 0, yPercent: -8, ease: "none",
    scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: 0.5 },
  });

  /* the semester rail draws to today */
  const fill = q("#railFill");
  if (fill) {
    gsap.set(fill, { scaleX: 0 });
    ScrollTrigger.create({
      trigger: "#dates", start: "top 60%", once: true,
      onEnter: () => gsap.to(fill, { scaleX: 1, duration: 0.9, ease: EASE }),
    });
  }

  /* the payoff ground wipes up — the accent arriving with force */
  gsap.fromTo("#join", { clipPath: "inset(12% 0 0 0)" }, {
    clipPath: "inset(0% 0 0 0)", ease: "none",
    scrollTrigger: { trigger: "#join", start: "top bottom", end: "top 55%", scrub: 0.6 },
  });
  gsap.from(".payoff-inner", {
    opacity: 0, y: 24, duration: 0.56, ease: EASE,
    scrollTrigger: { trigger: "#join", start: "top 62%", once: true },
  });

  /* the bar gets out of the way on the way down */
  let lastY = 0;
  ScrollTrigger.create({
    start: 0, end: "max",
    onUpdate: (self) => {
      const y = self.scroll();
      if (Math.abs(y - lastY) > 8) {
        bar.classList.toggle("is-hidden", y > 120 && y > lastY);
        lastY = y;
      }
    },
  });

  /* specs count up — receipts arriving, not decoration */
  qa("#specMajors, #specCourses, #specRules").forEach((el) => {
    const target = parseInt(el.textContent.replace(/,/g, ""), 10);
    const o = { n: 0 };
    ScrollTrigger.create({
      trigger: "#specs", start: "top 78%", once: true,
      onEnter: () => gsap.to(o, {
        n: target, duration: 1.2, ease: EASE,
        onUpdate: () => { el.textContent = Math.round(o.n).toLocaleString("en-US"); },
      }),
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
   waitlist — unchanged contract: POST {email, referral} -> {position, already}
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
      okEl.innerHTML = data.already
        ? `already on the list — you're #${n}<span class="period">.</span>`
        : data.position <= 100
          ? `you're in — #${n} of the first 100<span class="period">.</span>`
          : `you're in — #${n} on the list<span class="period">.</span>`;
      form.hidden = true; okEl.hidden = false;
    } catch (err) {
      fail((err.message || "something went wrong — try again.").toLowerCase());
    }
  });
}
