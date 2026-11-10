import {
  Activity,
  BookOpen,
  Building2,
  Calculator,
  CheckCircle2,
  Clapperboard,
  ClipboardList,
  CloudSun,
  Compass,
  Droplets,
  Film,
  Fish,
  FlaskConical,
  GraduationCap,
  Hammer,
  HandHeart,
  Handshake,
  HeartPulse,
  Mail,
  Megaphone,
  Microscope,
  Music,
  Network,
  Palette,
  Pill,
  Rocket,
  ScanBarcode,
  ShoppingBag,
  Sparkles,
  Truck,
  Wrench,
} from "lucide-react"
import type { OnetMiniIpItem, RiasecDimension } from "../../data/onetMiniIpQuestions"

export function OnetItemVisualIcon({
  iconKey,
}: {
  iconKey: OnetMiniIpItem["iconKey"]
}) {
  const Icon = getOnetIcon(iconKey)
  return (
    <div className="relative mx-auto grid size-20 sm:size-24 place-items-center rounded-[28px] border border-white/80 bg-gradient-to-br from-sky-400/90 via-sky-500/90 to-cyan-500/90 text-white shadow-[inset_0_2px_4px_rgba(255,255,255,0.6),0_16px_36px_rgba(14,165,233,0.28)] backdrop-blur-xl">
      <div className="pointer-events-none absolute -inset-3 rounded-[34px] bg-sky-400/25 blur-xl" />
      <Icon className="relative z-10 size-9 sm:size-11 stroke-[1.9]" />
    </div>
  )
}

export function LiveRiasecHexagon({
  scores,
}: {
  scores: Record<RiasecDimension, number>
}) {
  const dims: RiasecDimension[] = ["R", "I", "A", "S", "E", "C"]
  const cx = 110
  const cy = 110
  const maxR = 76

  const toPoint = (idx: number, pct: number) => {
    const angle = -Math.PI / 2 + (idx * Math.PI * 2) / 6
    const r = (Math.max(12, Math.min(100, pct)) / 100) * maxR
    return `${(cx + r * Math.cos(angle)).toFixed(1)},${(
      cy +
      r * Math.sin(angle)
    ).toFixed(1)}`
  }

  const labelPoint = (idx: number) => {
    const angle = -Math.PI / 2 + (idx * Math.PI * 2) / 6
    const r = maxR + 18
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    }
  }

  const polygonPoints = dims
    .map((d, i) => toPoint(i, scores[d] ?? 50))
    .join(" ")

  return (
    <svg viewBox="0 0 220 220" className="mx-auto h-52 w-52 select-none">
      {[25, 50, 75, 100].map((level) => (
        <polygon
          key={level}
          points={dims.map((_, i) => toPoint(i, level)).join(" ")}
          fill={level === 100 ? "rgba(240,249,255,0.55)" : "none"}
          stroke="rgba(14,165,233,0.18)"
          strokeWidth="1"
        />
      ))}

      {dims.map((d, i) => {
        const end = toPoint(i, 100).split(",")
        const lp = labelPoint(i)
        return (
          <g key={d}>
            <line
              x1={cx}
              y1={cy}
              x2={end[0]}
              y2={end[1]}
              stroke="rgba(14,165,233,0.18)"
              strokeWidth="1"
            />
            <text
              x={lp.x}
              y={lp.y + 4}
              textAnchor="middle"
              className="fill-sky-900 text-[13px] font-black"
            >
              {d}
            </text>
          </g>
        )
      })}

      <polygon
        points={polygonPoints}
        fill="rgba(14,165,233,0.28)"
        stroke="#0284c7"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />

      {dims.map((d, i) => {
        const pt = toPoint(i, scores[d] ?? 50).split(",")
        return (
          <circle
            key={d}
            cx={pt[0]}
            cy={pt[1]}
            r="4.5"
            fill="#0284c7"
            stroke="#ffffff"
            strokeWidth="1.5"
          />
        )
      })}
    </svg>
  )
}

function getOnetIcon(key: OnetMiniIpItem["iconKey"]) {
  switch (key) {
    case "hammer":
      return Hammer
    case "wrench":
      return Wrench
    case "fish":
      return Fish
    case "truck":
      return Truck
    case "check":
      return CheckCircle2
    case "pill":
      return Pill
    case "droplets":
      return Droplets
    case "flask":
      return FlaskConical
    case "microscope":
      return Microscope
    case "cloud":
      return CloudSun
    case "book":
      return BookOpen
    case "music":
      return Music
    case "film":
      return Film
    case "palette":
      return Palette
    case "clapperboard":
      return Clapperboard
    case "heart":
      return HeartPulse
    case "compass":
      return Compass
    case "activity":
      return Activity
    case "handheart":
      return HandHeart
    case "graduation":
      return GraduationCap
    case "building":
      return Building2
    case "rocket":
      return Rocket
    case "handshake":
      return Handshake
    case "megaphone":
      return Megaphone
    case "shopping":
      return ShoppingBag
    case "network":
      return Network
    case "calculator":
      return Calculator
    case "clipboard":
      return ClipboardList
    case "scan":
      return ScanBarcode
    case "mail":
      return Mail
    default:
      return Sparkles
  }
}
