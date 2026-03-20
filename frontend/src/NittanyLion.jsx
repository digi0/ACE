export default function NittanyLion({ size = 110 }) {
  return (
    <svg
      viewBox="0 0 200 230"
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size * (230 / 200)}
      style={{ display: "block", flexShrink: 0 }}
    >
      {/* ══════════════════════════════
          CAPE  (behind everything)
          ══════════════════════════════ */}
      <path d="M48 158 Q10 196 22 228 L100 204 Z"           fill="#1a2744" />
      <path d="M152 158 Q190 196 178 228 L100 204 Z"         fill="#1a2744" />
      <path d="M72 158 Q80 198 100 194 Q120 198 128 158 Z"  fill="#253660" />
      <path d="M48 158 Q10 196 22 228"   stroke="#c9a227" strokeWidth="2.8" fill="none" strokeLinecap="round" />
      <path d="M152 158 Q190 196 178 228" stroke="#c9a227" strokeWidth="2.8" fill="none" strokeLinecap="round" />
      <path d="M72 158 Q86 167 100 164 Q114 167 128 158"
            stroke="#c9a227" strokeWidth="2" fill="none" strokeLinecap="round" />

      {/* ══════════════════════════════
          BODY / SUIT
          ══════════════════════════════ */}
      <rect x="60" y="150" width="80" height="54" rx="11" fill="#1a2744" />
      <rect x="60" y="160" width="80" height="4.5" fill="#c9a227" opacity="0.5" />

      {/* Shield badge */}
      <path d="M100 165 L86 172 L86 187 Q86 198 100 203 Q114 198 114 187 L114 172 Z"
            fill="#c9a227" />
      <text x="100" y="190" textAnchor="middle" fill="#1a2744"
            fontSize="9" fontWeight="900" fontFamily="Inter, sans-serif" letterSpacing="1">
        ACE
      </text>

      {/* Arms + paws */}
      <path d="M60 158 Q36 166 30 186" stroke="#1a2744" strokeWidth="18" strokeLinecap="round" fill="none" />
      <ellipse cx="28" cy="189" rx="15" ry="12" fill="#E8C060" />
      <path d="M140 158 Q164 166 170 186" stroke="#1a2744" strokeWidth="18" strokeLinecap="round" fill="none" />
      <ellipse cx="172" cy="189" rx="15" ry="12" fill="#E8C060" />

      {/* ══════════════════════════════
          MANE  — 4 concentric layers
          ══════════════════════════════ */}
      <ellipse cx="100" cy="96" rx="82" ry="80" fill="#3D2005" />
      <ellipse cx="100" cy="93" rx="70" ry="68" fill="#7A4E0A" />
      <ellipse cx="100" cy="90" rx="58" ry="57" fill="#A87018" />
      <ellipse cx="100" cy="87" rx="48" ry="47" fill="#C9A227" />

      {/* ══════════════════════════════
          LION HEAD
          Wide at cheeks, tapers to chin.
          ══════════════════════════════ */}
      <path d="
        M 38 82
        Q 30 102  33 120
        Q 38 138  100 142
        Q 162 138 167 120
        Q 170 102  162 82
        Q 150 58   100 56
        Q  50 58    38 82
        Z
      " fill="#F0D080" />

      {/* Wide cheek puffs — key lion feature */}
      <ellipse cx="40"  cy="114" rx="18" ry="14" fill="#EAC868" />
      <ellipse cx="160" cy="114" rx="18" ry="14" fill="#EAC868" />

      {/* ══════════════════════════════
          EARS — small, round, on TOP of mane
          (lions have small round ears, not big pointed ones)
          ══════════════════════════════ */}
      <circle cx="60"  cy="54" r="15" fill="#9A6018" />
      <circle cx="60"  cy="54" r="9"  fill="#F0D080" />
      <circle cx="60"  cy="54" r="5"  fill="#D4960A" opacity="0.5" />

      <circle cx="140" cy="54" r="15" fill="#9A6018" />
      <circle cx="140" cy="54" r="9"  fill="#F0D080" />
      <circle cx="140" cy="54" r="5"  fill="#D4960A" opacity="0.5" />

      {/* ══════════════════════════════
          EYES — large amber iris, heavy brow
          ══════════════════════════════ */}
      {/* Whites */}
      <ellipse cx="78"  cy="88" rx="13" ry="11" fill="white" />
      <ellipse cx="122" cy="88" rx="13" ry="11" fill="white" />
      {/* Amber iris */}
      <circle cx="79"  cy="89" r="8.5" fill="#BF7010" />
      <circle cx="123" cy="89" r="8.5" fill="#BF7010" />
      {/* Slit pupil */}
      <ellipse cx="79"  cy="89" rx="4.5" ry="6.5" fill="#111" />
      <ellipse cx="123" cy="89" rx="4.5" ry="6.5" fill="#111" />
      {/* Shine */}
      <circle cx="82"  cy="85.5" r="2.8" fill="white" opacity="0.9" />
      <circle cx="126" cy="85.5" r="2.8" fill="white" opacity="0.9" />

      {/* Heavy brow ridge — gives authority */}
      <path d="M62 77 Q78 68 92 76"   stroke="#5A3008" strokeWidth="5"   fill="none" strokeLinecap="round" />
      <path d="M108 76 Q122 68 138 77" stroke="#5A3008" strokeWidth="5"   fill="none" strokeLinecap="round" />
      {/* Brow highlight */}
      <path d="M63 76 Q78 67 91 75"   stroke="#A07020" strokeWidth="1.8" fill="none" strokeLinecap="round" opacity="0.5" />
      <path d="M109 75 Q122 67 137 76" stroke="#A07020" strokeWidth="1.8" fill="none" strokeLinecap="round" opacity="0.5" />

      {/* ══════════════════════════════
          MUZZLE — WIDE, PROTRUDING
          This is the #1 feature that reads "lion"
          ══════════════════════════════ */}
      {/* Main muzzle oval — very wide */}
      <ellipse cx="100" cy="118" rx="34" ry="26" fill="#EDD070" />
      {/* Muzzle highlight for depth */}
      <ellipse cx="86"  cy="112" rx="10" ry="7"  fill="rgba(255,255,255,0.18)" />

      {/* ══════════════════════════════
          NOSE — wide, flat, prominent
          ══════════════════════════════ */}
      <path d="M87 107 Q100 98 113 107 Q110 116 100 117 Q90 116 87 107 Z"
            fill="#6A2008" />
      {/* Nose bridge */}
      <rect x="97" y="94" width="6" height="14" rx="3" fill="#9A3010" opacity="0.4" />
      {/* Nose highlight */}
      <ellipse cx="93" cy="106" rx="4" ry="2.5" fill="rgba(255,255,255,0.2)" />

      {/* ══════════════════════════════
          MOUTH
          ══════════════════════════════ */}
      <path d="M100 117 L100 125" stroke="#6A2008" strokeWidth="2"   strokeLinecap="round" />
      <path d="M80 125 Q90 134 100 131 Q110 134 120 125"
            stroke="#5A1808" strokeWidth="2.5" fill="none" strokeLinecap="round" />
      {/* Teeth hint */}
      <ellipse cx="93"  cy="131" rx="4.5" ry="3" fill="white" opacity="0.6" />
      <ellipse cx="107" cy="131" rx="4.5" ry="3" fill="white" opacity="0.6" />

      {/* ══════════════════════════════
          WHISKERS — long, 3 per side
          ══════════════════════════════ */}
      <line x1="6"   y1="109" x2="64" y2="116" stroke="#7A4A08" strokeWidth="1.6" strokeLinecap="round" opacity="0.6" />
      <line x1="6"   y1="118" x2="64" y2="119" stroke="#7A4A08" strokeWidth="1.6" strokeLinecap="round" opacity="0.6" />
      <line x1="6"   y1="127" x2="64" y2="122" stroke="#7A4A08" strokeWidth="1.6" strokeLinecap="round" opacity="0.6" />
      <line x1="136" y1="116" x2="194" y2="109" stroke="#7A4A08" strokeWidth="1.6" strokeLinecap="round" opacity="0.6" />
      <line x1="136" y1="119" x2="194" y2="118" stroke="#7A4A08" strokeWidth="1.6" strokeLinecap="round" opacity="0.6" />
      <line x1="136" y1="122" x2="194" y2="127" stroke="#7A4A08" strokeWidth="1.6" strokeLinecap="round" opacity="0.6" />
    </svg>
  );
}
