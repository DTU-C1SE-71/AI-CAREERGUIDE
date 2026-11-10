import type { RoleplayScene } from "../../data/roleplayScenes";

export function RoleplaySceneVisual({
  visualType,
  group,
  sceneBadge,
}: {
  visualType: RoleplayScene["visualType"];
  group: RoleplayScene["group"];
  sceneBadge: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-[22px] border border-sky-200/70 bg-gradient-to-br from-sky-900 via-sky-800 to-cyan-900 p-5 text-white shadow-[0_14px_34px_rgba(14,165,233,0.18)]">
      {/* Liquid Glass ambient glow */}
      <div className="pointer-events-none absolute -top-12 -right-12 h-40 w-40 rounded-full bg-cyan-400/25 blur-2xl" />
      <div className="pointer-events-none absolute -bottom-10 -left-10 h-36 w-36 rounded-full bg-sky-400/20 blur-2xl" />
      <div
        className="pointer-events-none absolute inset-0 opacity-20"
        style={{
          backgroundImage:
            "radial-gradient(circle at 2px 2px, rgba(186,230,253,0.45) 1px, transparent 0)",
          backgroundSize: "18px 18px",
        }}
      />

      <div className="relative z-10 flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[10px] font-extrabold uppercase tracking-wider text-sky-100 backdrop-blur-md">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-300 animate-pulse" />
          {sceneBadge}
        </span>
        <span className="rounded-lg border border-cyan-300/30 bg-cyan-400/15 px-2.5 py-0.5 text-[10px] font-black tracking-widest text-cyan-200">
          ZONE · {group}
        </span>
      </div>

      {/* Central Interactive Hologram Illustration */}
      <div className="relative z-10 my-3 flex h-32 items-center justify-center">
        {renderHologramSvg(visualType, group)}
      </div>
    </div>
  );
}

function renderHologramSvg(
  visualType: RoleplayScene["visualType"],
  group: RoleplayScene["group"]
) {
  switch (group) {
    case "R":
      return (
        <svg viewBox="0 0 260 110" className="h-full w-full max-w-[260px]">
          <defs>
            <linearGradient id="skyGlowR" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="100%" stopColor="#a5f3fc" />
            </linearGradient>
          </defs>
          {/* Isometric platform */}
          <polygon
            points="130,88 60,64 130,40 200,64"
            fill="rgba(56,189,248,0.16)"
            stroke="#7dd3fc"
            strokeWidth="1.5"
          />
          <polygon
            points="130,96 52,68 130,42 208,68"
            fill="none"
            stroke="rgba(165,243,252,0.35)"
            strokeDasharray="4 4"
          />
          {/* Robotic / Engineering Core */}
          {visualType === "architecture" ? (
            <g stroke="url(#skyGlowR)" strokeWidth="2" fill="none">
              <rect x="88" y="26" width="26" height="46" rx="3" fill="rgba(56,189,248,0.22)" />
              <rect x="118" y="14" width="30" height="58" rx="3" fill="rgba(103,232,249,0.28)" />
              <rect x="152" y="32" width="22" height="40" rx="3" fill="rgba(56,189,248,0.18)" />
              <line x1="74" y1="72" x2="188" y2="72" stroke="#e0f2fe" strokeWidth="2" />
            </g>
          ) : (
            <g>
              <circle
                cx="130"
                cy="48"
                r="24"
                fill="rgba(14,165,233,0.25)"
                stroke="#67e8f9"
                strokeWidth="2"
              />
              <circle
                cx="130"
                cy="48"
                r="14"
                fill="none"
                stroke="#e0f2fe"
                strokeWidth="2"
                strokeDasharray="6 4"
              />
              {/* Mechanical Arms / Drone Nodes */}
              <line x1="82" y1="30" x2="108" y2="42" stroke="#7dd3fc" strokeWidth="2.5" />
              <line x1="178" y1="30" x2="152" y2="42" stroke="#7dd3fc" strokeWidth="2.5" />
              <circle cx="78" cy="28" r="7" fill="#38bdf8" stroke="#e0f2fe" strokeWidth="1.5" />
              <circle cx="182" cy="28" r="7" fill="#38bdf8" stroke="#e0f2fe" strokeWidth="1.5" />
              <circle cx="130" cy="48" r="5" fill="#e0f2fe" />
            </g>
          )}
        </svg>
      );

    case "I":
      return (
        <svg viewBox="0 0 260 110" className="h-full w-full max-w-[260px]">
          {/* Neural / Molecular Network */}
          <g stroke="rgba(125,211,252,0.55)" strokeWidth="1.5">
            <line x1="65" y1="30" x2="112" y2="52" />
            <line x1="65" y1="76" x2="112" y2="52" />
            <line x1="112" y1="52" x2="152" y2="28" />
            <line x1="112" y1="52" x2="152" y2="78" />
            <line x1="152" y1="28" x2="198" y2="52" />
            <line x1="152" y1="78" x2="198" y2="52" />
            <line x1="112" y1="52" x2="198" y2="52" strokeDasharray="3 3" />
          </g>
          {[
            [65, 30, 7],
            [65, 76, 7],
            [112, 52, 12],
            [152, 28, 9],
            [152, 78, 9],
            [198, 52, 11],
          ].map(([cx, cy, r], i) => (
            <g key={i}>
              <circle
                cx={cx}
                cy={cy}
                r={Number(r) + 5}
                fill="rgba(34,211,238,0.16)"
              />
              <circle
                cx={cx}
                cy={cy}
                r={r}
                fill="#0284c7"
                stroke="#a5f3fc"
                strokeWidth="2"
              />
            </g>
          ))}
          <text
            x="130"
            y="100"
            textAnchor="middle"
            fill="#bae6fd"
            fontSize="9"
            fontWeight="700"
            letterSpacing="2"
          >
            {visualType === "biotech" ? "BIO-GENOME LAB" : "AI · DATA MATRIX"}
          </text>
        </svg>
      );

    case "A":
      return (
        <svg viewBox="0 0 260 110" className="h-full w-full max-w-[260px]">
          {/* Creative Floating Canvas & Sound/Motion Waves */}
          <rect
            x="58"
            y="18"
            width="92"
            height="62"
            rx="10"
            fill="rgba(56,189,248,0.2)"
            stroke="#7dd3fc"
            strokeWidth="1.8"
          />
          <rect
            x="108"
            y="30"
            width="94"
            height="60"
            rx="10"
            fill="rgba(6,182,212,0.28)"
            stroke="#cffafe"
            strokeWidth="1.8"
          />
          <circle cx="86" cy="42" r="9" fill="#67e8f9" />
          <path
            d="M 122 72 Q 142 44 160 66 T 190 48"
            fill="none"
            stroke="#e0f2fe"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          <circle cx="190" cy="48" r="4" fill="#ffffff" />
        </svg>
      );

    case "S":
      return (
        <svg viewBox="0 0 260 110" className="h-full w-full max-w-[260px]">
          {/* Human Connection Orbit & Pulse */}
          <circle
            cx="130"
            cy="54"
            r="38"
            fill="none"
            stroke="rgba(125,211,252,0.35)"
            strokeWidth="1.5"
            strokeDasharray="4 4"
          />
          <circle
            cx="130"
            cy="54"
            r="22"
            fill="rgba(56,189,248,0.25)"
            stroke="#67e8f9"
            strokeWidth="2"
          />
          {/* Heartbeat / Empathy Wave */}
          <polyline
            points="92,54 114,54 122,38 130,70 138,46 144,54 168,54"
            fill="none"
            stroke="#e0f2fe"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="78" cy="54" r="6" fill="#38bdf8" stroke="#bae6fd" strokeWidth="1.5" />
          <circle cx="182" cy="54" r="6" fill="#38bdf8" stroke="#bae6fd" strokeWidth="1.5" />
        </svg>
      );

    case "E":
      return (
        <svg viewBox="0 0 260 110" className="h-full w-full max-w-[260px]">
          {/* Ascending Strategy Bars & Launch Trajectory */}
          <rect x="64" y="64" width="20" height="26" rx="4" fill="rgba(56,189,248,0.3)" stroke="#7dd3fc" />
          <rect x="98" y="50" width="20" height="40" rx="4" fill="rgba(56,189,248,0.45)" stroke="#7dd3fc" />
          <rect x="132" y="36" width="20" height="54" rx="4" fill="rgba(34,211,238,0.6)" stroke="#a5f3fc" />
          <rect x="166" y="20" width="22" height="70" rx="4" fill="rgba(103,232,249,0.8)" stroke="#ffffff" />
          <path
            d="M 58 68 L 106 44 L 142 30 L 188 12"
            fill="none"
            stroke="#e0f2fe"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          <circle cx="188" cy="12" r="5" fill="#ffffff" />
        </svg>
      );

    case "C":
      return (
        <svg viewBox="0 0 260 110" className="h-full w-full max-w-[260px]">
          {/* Precision Shield & Structured Matrix */}
          <rect
            x="62"
            y="22"
            width="136"
            height="68"
            rx="10"
            fill="rgba(14,165,233,0.18)"
            stroke="#7dd3fc"
            strokeWidth="1.8"
          />
          <line x1="62" y1="42" x2="198" y2="42" stroke="rgba(125,211,252,0.5)" />
          <circle cx="76" cy="32" r="3" fill="#67e8f9" />
          <circle cx="86" cy="32" r="3" fill="#38bdf8" />
          <circle cx="96" cy="32" r="3" fill="#bae6fd" />
          {/* Checkmark Shield inside */}
          <polygon
            points="130,46 150,53 150,69 130,82 110,69 110,53"
            fill="rgba(34,211,238,0.3)"
            stroke="#e0f2fe"
            strokeWidth="1.8"
          />
          <polyline
            points="122,64 128,70 140,57"
            fill="none"
            stroke="#ffffff"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
  }
}
