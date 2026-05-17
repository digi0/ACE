import { useEffect, useId, useState } from "react";
import Particles, { initParticlesEngine } from "@tsparticles/react";
import { loadSlim } from "@tsparticles/slim";

/**
 * Aceternity-style animated sparkles background, ported manually (not via
 * shadcn) so ACE doesn't have to take on Tailwind. Wraps @tsparticles/react.
 *
 * Props:
 *  - id, className, background ("transparent" by default)
 *  - minSize, maxSize — particle dimensions
 *  - speed — opacity animation speed (default 4)
 *  - particleColor — hex string (default "#ffffff")
 *  - particleDensity — particle count (default 120)
 */
export default function SparklesCore({
  id,
  className,
  background = "transparent",
  minSize = 0.4,
  maxSize = 1,
  speed = 4,
  particleColor = "#ffffff",
  particleDensity = 120,
}) {
  const [init, setInit] = useState(false);
  const generatedId = useId();

  useEffect(() => {
    initParticlesEngine(async (engine) => {
      await loadSlim(engine);
    }).then(() => setInit(true));
  }, []);

  if (!init) return null;

  return (
    <div className={className}>
      <Particles
        id={id || generatedId}
        options={{
          background: { color: { value: background } },
          fullScreen: { enable: false, zIndex: 1 },
          fpsLimit: 120,
          interactivity: {
            events: {
              onClick: { enable: true, mode: "push" },
              onHover: { enable: false, mode: "repulse" },
              resize: true,
            },
            modes: {
              push: { quantity: 4 },
              repulse: { distance: 200, duration: 0.4 },
            },
          },
          particles: {
            bounce: {
              horizontal: { value: 1 },
              vertical: { value: 1 },
            },
            collisions: { enable: false },
            color: {
              value: particleColor,
              animation: { enable: true, speed: 100 },
            },
            move: {
              direction: "none",
              enable: true,
              outModes: { default: "out" },
              random: false,
              speed: { min: 0.1, max: 1 },
              straight: false,
            },
            number: {
              density: { enable: true, width: 400, height: 400 },
              limit: { mode: "delete", value: 0 },
              value: particleDensity,
            },
            opacity: {
              value: { min: 0.1, max: 1 },
              animation: { enable: true, speed: speed, startValue: "random", sync: false },
            },
            shape: { type: "circle" },
            size: { value: { min: minSize, max: maxSize } },
          },
          detectRetina: true,
        }}
      />
    </div>
  );
}
