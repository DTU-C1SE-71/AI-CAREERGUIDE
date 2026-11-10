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
import { useState } from "react"
import {
  RIASEC_META,
  type OnetMiniIpItem,
  type RiasecDimension,
} from "../../data/onetMiniIpQuestions"

export function QuestionIllustrationFrame({
  item,
  index,
  total,
}: {
  item: OnetMiniIpItem
  index: number
  total: number
}) {
  const [loaded, setLoaded] = useState(false)
  const [errored, setErrored] = useState(false)
  const Icon = getOnetIcon(item.iconKey)
  const meta = RIASEC_META[item.dimension]

  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-2xl border border-white/85 bg-gradient-to-br from-sky-100 via-sky-50 to-cyan-100 shadow-sm">
      {/* Skeleton Loading State */}
      {!loaded && !errored && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-gradient-to-r from-sky-100/80 via-white/90 to-sky-100/80 animate-pulse">
          <div className="grid size-12 place-items-center rounded-2xl bg-sky-500/15 text-sky-600">
            <Icon className="size-6 stroke-[2]" />
          </div>
          <span className="h-2 w-24 rounded-full bg-sky-200/70" />
        </div>
      )}

      {/* Contextual Real Photo Illustration */}
      {!errored ? (
        <img
          src={item.imageUrl}
          alt={item.titleVi}
          loading="lazy"
          draggable={false}
          onLoad={() => setLoaded(true)}
          onError={() => setErrored(true)}
          className={`h-full w-full select-none object-cover transition-all duration-500 ${
            loaded ? "scale-100 opacity-100" : "scale-105 opacity-0"
          }`}
        />
      ) : (
        /* Vector Illustration Fallback if offline */
        <div className="flex h-full w-full flex-col items-center justify-center bg-gradient-to-br from-sky-500 via-sky-600 to-cyan-500 p-6 text-white">
          <div className="grid size-16 place-items-center rounded-2xl border border-white/40 bg-white/20 shadow-md backdrop-blur-md">
            <Icon className="size-8 stroke-[2]" />
          </div>
        </div>
      )}

      {/* Subtle Gradient Overlay for Depth & Readability */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-slate-950/45 via-slate-900/5 to-transparent" />

      {/* Top Badges: Index + RIASEC Group Tag */}
      <div className="absolute inset-x-3 top-3 flex items-center justify-between gap-2">
        <span className="rounded-full border border-white/80 bg-white/85 px-3 py-1 text-xs font-black text-sky-900 shadow-sm backdrop-blur-md">
          {index + 1} / {total}
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-white/75 bg-white/85 px-3 py-1 text-xs font-extrabold text-sky-800 shadow-sm backdrop-blur-md">
          <Icon className="size-3.5 text-sky-600" />
          <span>{meta.tag}</span>
        </span>
      </div>
    </div>
  )
}

export function OnetItemVisualIcon({
  iconKey,
}: {
  iconKey: OnetMiniIpItem["iconKey"]
}) {
  const Icon = getOnetIcon(iconKey)
  return (
    <div className="relative mx-auto grid size-16 place-items-center rounded-2xl border border-white/80 bg-gradient-to-br from-sky-400/90 via-sky-500/90 to-cyan-500/90 text-white shadow-sm backdrop-blur-xl">
      <Icon className="relative z-10 size-8 stroke-[1.9]" />
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
