import {
  Atom,
  Briefcase,
  Building2,
  CheckCircle2,
  Compass,
  Cpu,
  Database,
  Dna,
  Film,
  Globe,
  HeartPulse,
  Megaphone,
  Music,
  Palette,
  PenTool,
  Plane,
  Radar,
  Rocket,
  Scale,
  ShieldCheck,
  Sparkles,
  Truck,
  Users,
  Wrench,
} from "lucide-react"
import type { LootItemCard } from "../../data/roleplayScenes"

export function LootItemIcon({
  iconKey,
  selectedRank,
}: {
  iconKey: LootItemCard["iconKey"]
  selectedRank: "FIRST_OR_BOOST" | "SECOND_OR_THIRD" | "NONE"
}) {
  const IconComponent = getIconComponent(iconKey)

  return (
    <div
      className={`relative grid size-11 shrink-0 place-items-center rounded-2xl border transition-all duration-200 ${
        selectedRank === "FIRST_OR_BOOST"
          ? "border-white/40 bg-white/20 text-white shadow-[0_0_20px_rgba(255,255,255,0.25)]"
          : selectedRank === "SECOND_OR_THIRD"
            ? "border-sky-300 bg-gradient-to-br from-sky-500 to-cyan-500 text-white shadow-sm"
            : "border-sky-100 bg-sky-50/80 text-sky-600 group-hover:border-sky-200 group-hover:bg-sky-100/80"
      }`}
    >
      <IconComponent className="size-5" />
    </div>
  )
}

function getIconComponent(iconKey: LootItemCard["iconKey"]) {
  switch (iconKey) {
    case "wrench":
      return Wrench
    case "cpu":
      return Cpu
    case "palette":
      return Palette
    case "heart":
      return HeartPulse
    case "rocket":
      return Rocket
    case "shield":
      return ShieldCheck
    case "drone":
      return Plane
    case "dna":
      return Dna
    case "film":
      return Film
    case "users":
      return Users
    case "briefcase":
      return Briefcase
    case "database":
      return Database
    case "compass":
      return Compass
    case "radar":
      return Radar
    case "pen":
      return PenTool
    case "sparkles":
      return Sparkles
    case "scale":
      return Scale
    case "check":
      return CheckCircle2
    case "building":
      return Building2
    case "atom":
      return Atom
    case "music":
      return Music
    case "globe":
      return Globe
    case "megaphone":
      return Megaphone
    case "truck":
      return Truck
    default:
      return Sparkles
  }
}
