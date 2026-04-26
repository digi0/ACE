import { useEffect, useCallback } from "react";

export default function ParticlesBackground() {
  const initParticles = useCallback((isDark) => {
    const oldCanvas = document.querySelector("#particles-js canvas");
    if (oldCanvas) oldCanvas.remove();

    if (window.pJSDom?.length > 0) {
      window.pJSDom.forEach((p) => p.pJS.fn.vendors.destroypJS());
      window.pJSDom = [];
    }

    const colors = isDark
      ? { particles: "#00f5ff", lines: "#00d9ff", accent: "#0096c7" }
      : { particles: "#0277bd", lines: "#0288d1", accent: "#039be5" };

    window.particlesJS("particles-js", {
      particles: {
        number: { value: 140, density: { enable: true, value_area: 800 } },
        color: { value: colors.particles },
        shape: { type: "circle", stroke: { width: 0.5, color: colors.accent } },
        opacity: {
          value: 0.7,
          random: true,
          anim: { enable: true, speed: 1, opacity_min: 0.3 },
        },
        size: {
          value: 3,
          random: true,
          anim: { enable: true, speed: 2, size_min: 1 },
        },
        line_linked: {
          enable: true,
          distance: 160,
          color: colors.lines,
          opacity: 0.4,
          width: 1.2,
        },
        move: { enable: true, speed: 2, random: true, out_mode: "bounce" },
      },
      interactivity: {
        detect_on: "canvas",
        events: {
          onhover: { enable: true, mode: "grab" },
          onclick: { enable: true, mode: "push" },
          resize: true,
        },
        modes: {
          grab: { distance: 220, line_linked: { opacity: 0.8 } },
          push: { particles_nb: 4 },
          repulse: { distance: 180, duration: 0.4 },
        },
      },
      retina_detect: true,
    });
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const detectDark = () => {
      const html = document.documentElement;
      return (
        html.classList.contains("dark") ||
        html.getAttribute("data-theme") === "dark"
      );
    };

    let observer;
    let scriptEl;

    const start = () => {
      initParticles(detectDark());
      observer = new MutationObserver(() => initParticles(detectDark()));
      observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["class", "data-theme"],
      });
    };

    if (window.particlesJS) {
      start();
    } else {
      scriptEl = document.createElement("script");
      scriptEl.src =
        "https://cdn.jsdelivr.net/particles.js/2.0.0/particles.min.js";
      scriptEl.async = true;
      scriptEl.onload = start;
      document.body.appendChild(scriptEl);
    }

    return () => {
      observer?.disconnect();
      if (window.pJSDom?.length > 0) {
        window.pJSDom.forEach((p) => p.pJS.fn.vendors.destroypJS());
        window.pJSDom = [];
      }
      if (scriptEl && scriptEl.parentNode) {
        scriptEl.parentNode.removeChild(scriptEl);
      }
    };
  }, [initParticles]);

  return (
    <div
      id="particles-js"
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        zIndex: 0,
        background:
          "linear-gradient(45deg, #000814 0%, #003566 50%, #0077b6 100%)",
        transition: "background 0.5s ease",
      }}
    />
  );
}
