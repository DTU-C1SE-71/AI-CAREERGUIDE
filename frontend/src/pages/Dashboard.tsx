import {
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  Clock,
  Compass,
  Download,
  Eye,
  GraduationCap,
  History,
  RotateCcw,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router"
import { Badge } from "../components/common/Badge"
import { Button } from "../components/common/Button"
import { Card } from "../components/common/Card"
import { PageContainer } from "../components/layout/PageContainer"
import { RiasecRadarChart } from "../components/visualization/RiasecRadarChart"
import { TwoTierFunnelRecommendation } from "../components/xai/TwoTierFunnelRecommendation"
import { useAuth } from "../context/AuthContext"
import { MOET_435_MAJORS } from "../data/moetMajors435"
import { useAssessment } from "../hooks/useAssessment"
import { apiRequest } from "../services/api"
import {
  riasecData as fallbackRiasec,
  type RiasecRadarPoint,
} from "../services/mockData"
import type { FunnelRecommendationData, Major } from "../types/major"

interface DashboardOverviewPayload {
  user_name?: string
  riasecData?: RiasecRadarPoint[]
  scoreBarData?: Array<{ name: string; value: number }>
  majors?: Major[]
  funnel?: FunnelRecommendationData
}

interface TaxonomyCatalogItem {
  major_code: string
  name_vi?: string
  name?: string
  category?: string
  description?: string
  subject_blocks?: string[]
  blocks?: string[]
}

const ARCHETYPES: Record<string, string> = {
  I: "Nhà nghiên cứu Khoa học",
  R: "Kỹ sư Thực hành & Công nghệ",
  A: "Nhà sáng tạo Nghệ thuật",
  S: "Chuyên gia Phát triển Con người",
  E: "Nhà lãnh đạo Kinh doanh",
  C: "Chuyên gia Quản trị Dữ liệu",
}

interface DynamicFieldTemplate {
  field_name: string
  icon: string
  primaryDim: string
  secondaryDim: string
  majors: Array<{
    id: string
    code: string
    name: string
    university: string
    minCutoff: number
    replacesHighMajor?: string
    primaryWeight: number
    secondaryWeight: number
    gaps: string[]
    summary: string
  }>
}

const DYNAMIC_FIELD_TEMPLATES: DynamicFieldTemplate[] = [
  {
    field_name: "Máy tính & Công nghệ thông tin",
    icon: "💻",
    primaryDim: "I",
    secondaryDim: "R",
    majors: [
      {
        id: "computer-science",
        code: "480101",
        name: "Khoa học máy tính",
        university: "Khối A00, A01 · Chuẩn TT74/2026 (Cạnh tranh cao ≥ 24.5đ)",
        minCutoff: 24.0,
        primaryWeight: 0.65,
        secondaryWeight: 0.35,
        gaps: ["Tư duy thuật toán", "Tiếng Anh chuyên ngành", "Kỹ năng làm dự án"],
        summary:
          "Phù hợp nổi trội với năng lực Nghiên cứu (I) và Thực hành kỹ thuật (R), kết hợp tư duy toán học & giải quyết vấn đề.",
      },
      {
        id: "artificial-intelligence",
        code: "480107",
        name: "Trí tuệ nhân tạo",
        university: "Khối A00, A01, D07 · Chuẩn TT74/2026 (Cạnh tranh cao ≥ 25.0đ)",
        minCutoff: 24.5,
        primaryWeight: 0.7,
        secondaryWeight: 0.3,
        gaps: ["Xác suất thống kê", "Python & Học máy", "Đại số tuyến tính"],
        summary:
          "Tối ưu cho học sinh có thiên hướng phân tích định lượng, khám phá quy luật dữ liệu và mô hình AI.",
      },
      {
        id: "software-engineering",
        code: "480103",
        name: "Kỹ thuật phần mềm",
        university: "Khối A00, A01, D01 · Chuẩn TT74/2026 (Khá ≥ 20.5đ)",
        minCutoff: 20.0,
        replacesHighMajor: "Khoa học máy tính / Trí tuệ nhân tạo (≥ 24.5đ)",
        primaryWeight: 0.55,
        secondaryWeight: 0.45,
        gaps: ["Kiến trúc phần mềm", "Cơ sở dữ liệu", "Lập trình web"],
        summary:
          "Cân bằng giữa tư duy hệ thống và năng lực xây dựng sản phẩm công nghệ thực tiễn.",
      },
      {
        id: "information-systems",
        code: "480104",
        name: "Hệ thống thông tin",
        university: "Khối A00, A01, D01 · Chuẩn TT74/2026 (Vừa sức ≥ 18.5đ)",
        minCutoff: 18.0,
        replacesHighMajor: "Khoa học máy tính / Kỹ thuật phần mềm",
        primaryWeight: 0.6,
        secondaryWeight: 0.4,
        gaps: ["Phân tích nghiệp vụ (BA)", "Cơ sở dữ liệu SQL", "Quản trị hệ thống"],
        summary:
          "Phương án vừa sức cùng nhóm Máy tính (4801), kết nối giải pháp phần mềm với vận hành doanh nghiệp.",
      },
      {
        id: "computer-engineering-tech",
        code: "480108",
        name: "Công nghệ kỹ thuật máy tính",
        university: "Khối A00, A01, D01 · Chuẩn TT74/2026 (Tiêu chuẩn ≥ 15.5đ)",
        minCutoff: 15.0,
        replacesHighMajor: "Khoa học máy tính / Kỹ thuật phần mềm",
        primaryWeight: 0.5,
        secondaryWeight: 0.5,
        gaps: ["Thực hành mạng & phần cứng", "Lập trình căn bản", "Quản trị hệ thống"],
        summary:
          "Ngành ứng dụng thực hành có ngưỡng điểm an toàn, giữ trọn đam mê Công nghệ thông tin.",
      },
    ],
  },
  {
    field_name: "Kinh doanh & Quản lý",
    icon: "📊",
    primaryDim: "E",
    secondaryDim: "S",
    majors: [
      {
        id: "international-business",
        code: "340120",
        name: "Kinh doanh quốc tế",
        university: "Khối A01, D01, D07 · Chuẩn TT74/2026 (Cạnh tranh cao ≥ 24.5đ)",
        minCutoff: 24.0,
        primaryWeight: 0.65,
        secondaryWeight: 0.35,
        gaps: ["Ngoại thương", "Tiếng Anh thương mại", "Đàm phán quốc tế"],
        summary:
          "Định hướng toàn cầu cho học sinh nổi trội nhóm Quản lý (E) và năng lực ngoại ngữ.",
      },
      {
        id: "digital-marketing",
        code: "340115",
        name: "Marketing",
        university: "Khối A01, D01, C00 · Chuẩn TT74/2026 (Khá ≥ 20.5đ)",
        minCutoff: 20.0,
        replacesHighMajor: "Kinh doanh quốc tế (≥ 24.5đ)",
        primaryWeight: 0.6,
        secondaryWeight: 0.4,
        gaps: ["Chiến lược nội dung", "Phân tích hành vi", "Digital Ads"],
        summary:
          "Phát huy thế mạnh Quản lý (E) và Xã hội (S) trong môi trường truyền thông, thương hiệu và dữ liệu khách hàng.",
      },
      {
        id: "e-commerce",
        code: "340122",
        name: "Thương mại điện tử",
        university: "Khối A00, A01, D01 · Chuẩn TT74/2026 (Vừa sức ≥ 18.5đ)",
        minCutoff: 18.0,
        replacesHighMajor: "Kinh doanh quốc tế / Marketing",
        primaryWeight: 0.65,
        secondaryWeight: 0.35,
        gaps: ["Vận hành chuỗi cung ứng", "SEO & Digital Ads", "Tài chính số"],
        summary:
          "Giao thoa giữa tư duy kinh doanh hiện đại và vận hành nền tảng số đa kênh.",
      },
      {
        id: "commercial-business",
        code: "340121",
        name: "Kinh doanh thương mại",
        university: "Khối A00, A01, D01 · Chuẩn TT74/2026 (Tiêu chuẩn ≥ 15.5đ)",
        minCutoff: 15.0,
        replacesHighMajor: "Kinh doanh quốc tế / Marketing",
        primaryWeight: 0.6,
        secondaryWeight: 0.4,
        gaps: ["Nghiệp vụ bán hàng", "Quản trị bán lẻ", "Giao tiếp khách hàng"],
        summary:
          "Phương án vừa sức trong cùng nhóm Kinh doanh (3401), sát thực tế thị trường và có cơ hội việc làm rộng mở.",
      },
    ],
  },
  {
    field_name: "Kỹ thuật & Công nghệ kỹ thuật",
    icon: "⚙️",
    primaryDim: "R",
    secondaryDim: "I",
    majors: [
      {
        id: "ic-design",
        code: "520202",
        name: "Thiết kế vi mạch",
        university: "Khối A00, A01 · Chuẩn TT74/2026 (Cạnh tranh cao ≥ 24.5đ)",
        minCutoff: 24.0,
        primaryWeight: 0.55,
        secondaryWeight: 0.45,
        gaps: ["Vật lý bán dẫn", "Thiết kế mạch số", "Tiếng Anh kỹ thuật"],
        summary:
          "Ngành mũi nhọn chiến lược cho học sinh xuất sắc khối Tự nhiên và đam mê phần cứng vi mạch.",
      },
      {
        id: "electronics-telecom",
        code: "520207",
        name: "Kỹ thuật điện tử - viễn thông",
        university: "Khối A00, A01 · Chuẩn TT74/2026 (Khá ≥ 19.5đ)",
        minCutoff: 19.0,
        replacesHighMajor: "Thiết kế vi mạch (≥ 24.5đ)",
        primaryWeight: 0.6,
        secondaryWeight: 0.4,
        gaps: ["Mạch điện tử", "Xử lý tín hiệu số", "IoT thực hành"],
        summary:
          "Phù hợp với học sinh yêu thích thiết bị phần cứng, vi mạch và mạng truyền thông thế hệ mới.",
      },
      {
        id: "automation-tech",
        code: "510303",
        name: "Công nghệ kỹ thuật điều khiển & Tự động hóa",
        university: "Khối A00, A01, C01 · Chuẩn TT74/2026 (Tiêu chuẩn ≥ 15.5đ)",
        minCutoff: 15.0,
        replacesHighMajor: "Thiết kế vi mạch / Kỹ thuật cơ điện tử (Lĩnh vực 52)",
        primaryWeight: 0.7,
        secondaryWeight: 0.3,
        gaps: ["Vi điều khiển PLC", "Hệ thống nhúng", "Bản vẽ kỹ thuật"],
        summary:
          "Chuyển dịch sang nhánh Công nghệ Kỹ thuật ứng dụng (5103): giữ trọn đam mê kỹ thuật với điểm chuẩn vừa sức.",
      },
    ],
  },
  {
    field_name: "Nghệ thuật & Truyền thông số",
    icon: "🎨",
    primaryDim: "A",
    secondaryDim: "S",
    majors: [
      {
        id: "multimedia-comm",
        code: "320104",
        name: "Truyền thông đa phương tiện",
        university: "Khối D01, C00, A01 · Chuẩn TT74/2026 (Khá ≥ 21.0đ)",
        minCutoff: 20.5,
        primaryWeight: 0.55,
        secondaryWeight: 0.45,
        gaps: ["Kịch bản truyền thông", "Sản xuất nội dung số", "Kỹ năng thuyết trình"],
        summary:
          "Kết hợp khả năng sáng tạo nội dung (A) và thấu cảm kết nối cộng đồng (S).",
      },
      {
        id: "graphic-design",
        code: "210403",
        name: "Thiết kế đồ họa",
        university: "Khối D01, H00, V00 · Chuẩn TT74/2026 (Vừa sức ≥ 18.0đ)",
        minCutoff: 17.5,
        replacesHighMajor: "Truyền thông đa phương tiện",
        primaryWeight: 0.75,
        secondaryWeight: 0.25,
        gaps: ["Tư duy thị giác", "Bố cục màu sắc", "Công cụ thiết kế số"],
        summary:
          "Tối ưu cho nhóm Nghệ thuật (A) nổi trội, yêu thích sáng tạo hình ảnh, UI/UX và truyền thông thị giác.",
      },
      {
        id: "media-tech",
        code: "320106",
        name: "Công nghệ truyền thông",
        university: "Khối D01, C00, A01 · Chuẩn TT74/2026 (Tiêu chuẩn ≥ 15.5đ)",
        minCutoff: 15.0,
        replacesHighMajor: "Truyền thông đa phương tiện",
        primaryWeight: 0.65,
        secondaryWeight: 0.35,
        gaps: ["Sản xuất media", "Thiết kế đa phương tiện", "Quản trị kênh số"],
        summary:
          "Phương án vừa sức trong cùng nhóm Báo chí & Truyền thông (3201), chú trọng kỹ năng thực hành.",
      },
    ],
  },
  {
    field_name: "Khoa học Giáo dục & Xã hội",
    icon: "🤝",
    primaryDim: "S",
    secondaryDim: "A",
    majors: [
      {
        id: "psychology",
        code: "310401",
        name: "Tâm lý học",
        university: "Khối B00, C00, D01 · Chuẩn TT74/2026 (Khá ≥ 21.0đ)",
        minCutoff: 20.5,
        primaryWeight: 0.7,
        secondaryWeight: 0.3,
        gaps: ["Kỹ năng lắng nghe sâu", "Phương pháp nghiên cứu tâm lý", "Thống kê xã hội"],
        summary:
          "Phù hợp cao với nhóm Xã hội (S), giàu sự đồng cảm, lắng nghe và hỗ trợ phát triển con người.",
      },
      {
        id: "ed-tech",
        code: "140103",
        name: "Công nghệ giáo dục",
        university: "Khối D01, C00, A01 · Chuẩn TT74/2026 (Vừa sức ≥ 18.0đ)",
        minCutoff: 17.5,
        replacesHighMajor: "Sư phạm / Tâm lý học",
        primaryWeight: 0.65,
        secondaryWeight: 0.35,
        gaps: ["Thiết kế học liệu số", "Hệ thống LMS", "Sư phạm tương tác"],
        summary:
          "Ngành hiện đại thuộc nhóm Khoa học giáo dục (1401), điểm chuẩn vừa sức và không bị áp lực điểm chuẩn Sư phạm.",
      },
      {
        id: "social-work",
        code: "760101",
        name: "Công tác xã hội",
        university: "Khối C00, D01 · Chuẩn TT74/2026 (Tiêu chuẩn ≥ 15.0đ)",
        minCutoff: 15.0,
        replacesHighMajor: "Tâm lý học / Sư phạm",
        primaryWeight: 0.75,
        secondaryWeight: 0.25,
        gaps: ["Tham vấn cộng đồng", "Giao tiếp xã hội", "Quản lý dự án xã hội"],
        summary:
          "Phương án an toàn cho học sinh nhóm Xã hội (S), phát huy trọn vẹn năng lực hỗ trợ cộng đồng.",
      },
    ],
  },
  {
    field_name: "Tài chính - Kế toán & Quản trị",
    icon: "🏛️",
    primaryDim: "C",
    secondaryDim: "E",
    majors: [
      {
        id: "fintech",
        code: "340205",
        name: "Công nghệ tài chính (Fintech)",
        university: "Khối A00, A01, D01 · Chuẩn TT74/2026 (Cạnh tranh cao ≥ 24.0đ)",
        minCutoff: 23.5,
        primaryWeight: 0.6,
        secondaryWeight: 0.4,
        gaps: ["Phân tích dữ liệu tài chính", "Thuật toán định lượng", "Ngân hàng số"],
        summary:
          "Ngành mũi nhọn kết hợp Nghiệp vụ tài chính (C) và Công nghệ số hiện đại.",
      },
      {
        id: "finance-banking",
        code: "340201",
        name: "Tài chính - Ngân hàng",
        university: "Khối A00, A01, D01 · Chuẩn TT74/2026 (Khá ≥ 19.5đ)",
        minCutoff: 19.0,
        replacesHighMajor: "Công nghệ tài chính (Fintech)",
        primaryWeight: 0.65,
        secondaryWeight: 0.35,
        gaps: ["Phân tích báo cáo tài chính", "Kinh tế lượng", "Quản trị rủi ro"],
        summary:
          "Phát huy tối đa tính chính xác, hệ thống của nhóm Nghiệp vụ (C) và tư duy chiến lược (E).",
      },
      {
        id: "accounting",
        code: "340301",
        name: "Kế toán",
        university: "Khối A00, A01, D01 · Chuẩn TT74/2026 (Tiêu chuẩn ≥ 15.5đ)",
        minCutoff: 15.0,
        replacesHighMajor: "Tài chính - Ngân hàng / Fintech",
        primaryWeight: 0.7,
        secondaryWeight: 0.3,
        gaps: ["Chuẩn mực kế toán", "Excel & Phần mềm ERP", "Kiểm soát nội bộ"],
        summary:
          "Phương án an toàn và ổn định cao cho học sinh có thiên hướng Nghiệp vụ (C).",
      },
    ],
  },
]

function formatDateTimeVi(iso?: string): string {
  if (!iso) return "Vừa xong"
  try {
    const d = new Date(iso)
    return d.toLocaleString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    })
  } catch {
    return iso
  }
}

export function Dashboard() {
  const { user } = useAuth()
  const {
    assessment,
    history,
    activeHistoryId,
    reset,
    selectHistoryAttempt,
    deleteHistoryAttempt,
  } = useAssessment()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [data, setData] = useState<DashboardOverviewPayload | null>(null)
  const [catalog, setCatalog] = useState<TaxonomyCatalogItem[]>(MOET_435_MAJORS)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedCategory, setSelectedCategory] = useState("ALL")
  const [showAllCatalog, setShowAllCatalog] = useState(false)
  const [showHistoryDrawer, setShowHistoryDrawer] = useState(false)
  const catalogRef = useRef<HTMLDivElement>(null)
  const reportTopRef = useRef<HTMLDivElement>(null)

  const hasCompletedAssessment = useMemo(() => {
    const hasAnswers = Object.keys(assessment.answers || {}).length >= 3
    const hasScores = (assessment.scores || []).length >= 2
    return Boolean(
      (assessment.completed && (hasAnswers || hasScores)) || history.length > 0,
    )
  }, [assessment.completed, assessment.answers, assessment.scores, history.length])

  useEffect(() => {
    let mounted = true
    if (hasCompletedAssessment) {
      apiRequest<DashboardOverviewPayload | null>(
        "/recommender/dashboard/overview",
        null,
      )
        .then((res) => {
          if (mounted && res) {
            setData(res)
          }
        })
        .catch(() => {})
    }

    apiRequest<TaxonomyCatalogItem[] | null>(
      "/taxonomy/majors?limit=500",
      MOET_435_MAJORS,
    )
      .then((list) => {
        if (mounted && list && Array.isArray(list) && list.length >= 400) {
          setCatalog(list)
        }
      })
      .catch(() => {})

    return () => {
      mounted = false
    }
  }, [hasCompletedAssessment])

  useEffect(() => {
    if (searchParams.get("search") === "1" && catalogRef.current) {
      catalogRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [searchParams])

  // Merge user's live/selected assessment answers & scores into RIASEC radar data
  const displayedRiasec: RiasecRadarPoint[] = useMemo(() => {
    const base =
      data?.riasecData && data.riasecData.length > 0
        ? data.riasecData
        : fallbackRiasec

    const hasUserAnswers = Object.keys(assessment.answers || {}).length >= 3
    const hasUserScores = (assessment.scores || []).length >= 2

    if (!hasUserAnswers && !hasUserScores) {
      return base
    }

    const scoreMap = Object.fromEntries(
      (assessment.scores || []).map((s) => [s.subject, s.score]),
    )
    const getSubjPct = (s1: string, s2: string, fallbackVal: number) => {
      const v1 = scoreMap[s1]
      const v2 = scoreMap[s2]
      if (v1 !== undefined && v2 !== undefined)
        return Math.min(100, Math.round(((v1 + v2) / 2) * 10))
      if (v1 !== undefined) return Math.min(100, Math.round(v1 * 10))
      if (v2 !== undefined) return Math.min(100, Math.round(v2 * 10))
      return fallbackVal
    }

    return base.map((point) => {
      let interestVal = point.value
      if (hasUserAnswers) {
        const dimVals: number[] = []
        for (let i = 1; i <= 5; i++) {
          const v = assessment.answers[`${point.key}${i}`]
          if (typeof v === "number" && v > 0) dimVals.push(v)
        }
        if (dimVals.length > 0) {
          const avg = dimVals.reduce((a, b) => a + b, 0) / dimVals.length
          interestVal = Math.round((avg / 5) * 100)
        }
      }

      let acadVal = point.academicValue ?? point.value
      if (hasUserScores) {
        if (point.key === "R")
          acadVal = getSubjPct("Vật lý", "Toán", acadVal)
        else if (point.key === "I")
          acadVal = getSubjPct("Toán", "Hóa học", acadVal)
        else if (point.key === "A")
          acadVal = getSubjPct("Ngữ văn", "Tiếng Anh", acadVal)
        else if (point.key === "S")
          acadVal = getSubjPct("Ngữ văn", "Sinh học", acadVal)
        else if (point.key === "E")
          acadVal = getSubjPct("Tiếng Anh", "Toán", acadVal)
        else if (point.key === "C")
          acadVal = getSubjPct("Toán", "Tiếng Anh", acadVal)
      }

      return {
        ...point,
        value: interestVal,
        academicValue: acadVal,
      }
    })
  }, [data?.riasecData, assessment.answers, assessment.scores])

  const top3Dimensions = useMemo(() => {
    return [...displayedRiasec]
      .sort((a, b) => b.value - a.value)
      .slice(0, 3)
  }, [displayedRiasec])

  const hollandCodeBadge = useMemo(
    () => top3Dimensions.map((d) => d.key).join(" · "),
    [top3Dimensions],
  )

  const archetypeTitle = useMemo(() => {
    const primaryKey = top3Dimensions[0]?.key || "I"
    return ARCHETYPES[primaryKey] || "Nhà nghiên cứu Khoa học"
  }, [top3Dimensions])

  const bestBlockStats = useMemo(() => {
    if (!assessment.scores || assessment.scores.length < 3) {
      return {
        block: "Khối A00",
        rawSum: 25.0,
        zScore: "+1.18",
        percentile: "Top 12%",
      }
    }
    const sm = Object.fromEntries(
      assessment.scores.map((s) => [s.subject, s.score]),
    )
    const blocks = [
      {
        name: "Khối A00",
        sum: (sm["Toán"] || 7.5) + (sm["Vật lý"] || 7.5) + (sm["Hóa học"] || 7.5),
      },
      {
        name: "Khối A01",
        sum:
          (sm["Toán"] || 7.5) +
          (sm["Vật lý"] || 7.5) +
          (sm["Tiếng Anh"] || 7.5),
      },
      {
        name: "Khối D01",
        sum:
          (sm["Toán"] || 7.5) +
          (sm["Ngữ văn"] || 7.5) +
          (sm["Tiếng Anh"] || 7.5),
      },
      {
        name: "Khối B00",
        sum:
          (sm["Toán"] || 7.5) +
          (sm["Hóa học"] || 7.5) +
          (sm["Sinh học"] || 7.5),
      },
    ].sort((a, b) => b.sum - a.sum)

    const best = blocks[0]
    const z = (best.sum - 21.3) / 3.2
    const zStr = `${z >= 0 ? "+" : ""}${z.toFixed(2)}`
    const pct =
      z >= 1.2
        ? "Top 10%"
        : z >= 0.8
          ? "Top 18%"
          : z >= 0.3
            ? "Top 30%"
            : "Top 45%"
    return {
      block: best.name,
      rawSum: Number(best.sum.toFixed(1)),
      zScore: zStr,
      percentile: pct,
    }
  }, [assessment.scores])

  const cognitiveScorePct = useMemo(() => {
    const cogCount = Object.keys(assessment.cognitive || {}).length
    return Math.min(96, 82 + Math.min(14, cogCount * 2))
  }, [assessment.cognitive])

  // Dynamically compute 2-Tier Funnel Recommendations with Hard Academic Cutoff & Sibling Substitution
  const displayedFunnel: FunnelRecommendationData = useMemo(() => {
    const dimMap = Object.fromEntries(
      displayedRiasec.map((d) => [d.key, d]),
    )
    const studentBestSum = bestBlockStats.rawSum

    const computedFields = DYNAMIC_FIELD_TEMPLATES.map((tpl) => {
      const pDim = dimMap[tpl.primaryDim] || { value: 75, academicValue: 75 }
      const sDim = dimMap[tpl.secondaryDim] || { value: 70, academicValue: 70 }

      // Hard Gatekeeper: Filter OUT high-cutoff majors if student's score is below minCutoff
      const eligibleTemplates = tpl.majors.filter(
        (m) => studentBestSum >= m.minCutoff,
      )
      const hadBlockedHighMajor = eligibleTemplates.length < tpl.majors.length
      const activeTemplates =
        eligibleTemplates.length > 0
          ? eligibleTemplates
          : [tpl.majors[tpl.majors.length - 1]]

      const computedMajors: Major[] = activeTemplates
        .map((m) => {
          const interestFit = Math.min(
            99,
            Math.max(
              55,
              Math.round(
                pDim.value * m.primaryWeight + sDim.value * m.secondaryWeight,
              ),
            ),
          )
          // Target-Anchored Academic Fit: reward majors whose cutoff aligns with student's score
          const gap = studentBestSum - m.minCutoff
          const anchoredBoost = gap >= 0 && gap <= 4.5 ? 6 : 0
          const academicFit = Math.min(
            99,
            Math.max(
              55,
              Math.round(
                (pDim.academicValue ?? pDim.value) * m.primaryWeight +
                  (sDim.academicValue ?? sDim.value) * m.secondaryWeight +
                  anchoredBoost,
              ),
            ),
          )
          const cogFit = cognitiveScorePct
          const totalMatch = Math.min(
            98,
            Math.max(
              58,
              Math.round(
                0.45 * interestFit + 0.35 * academicFit + 0.2 * cogFit,
              ),
            ),
          )

          const substitutionNote =
            hadBlockedHighMajor && m.replacesHighMajor
              ? `\n\n> **Đề xuất thay thế vừa sức:** Do tổng điểm hiện tại (**${studentBestSum}đ** - ${bestBlockStats.block}) chưa đủ ngưỡng an toàn của ngành *${m.replacesHighMajor}*, hệ thống tự động đề xuất ngành tương đồng **${m.name}** (điểm sàn tham chiếu **≥ ${m.minCutoff}đ**) để tối ưu cơ hội trúng tuyển.`
              : ""

          return {
            id: m.id,
            code: m.code,
            name: m.name,
            category: tpl.field_name,
            university: m.university,
            match: totalMatch,
            feasibility: "TARGET" as const,
            fit: {
              interest: interestFit,
              academic: academicFit,
              cognitive: cogFit,
            },
            explanation: `### Vì sao phù hợp?\n${m.summary} (Độ tương thích Sở thích **${interestFit}%**, Học lực **${academicFit}%**, Nhận thức **${cogFit}%**).${substitutionNote}`,
            gaps: m.gaps,
          }
        })
        .sort((a, b) => b.match - a.match)

      const fieldMatch =
        computedMajors.length > 0
          ? Math.round(
              computedMajors.reduce((acc, item) => acc + item.match, 0) /
                computedMajors.length,
            )
          : 75

      return {
        field_name: tpl.field_name,
        icon: tpl.icon,
        match: fieldMatch,
        majors_count: computedMajors.length,
        majors: computedMajors.slice(0, 3),
      }
    })
      .sort((a, b) => b.match - a.match)
      .slice(0, 3)

    const allMajors = computedFields.flatMap((f) => f.majors)
    return {
      tier1_fields: computedFields,
      all_majors: allMajors,
    }
  }, [displayedRiasec, cognitiveScorePct, bestBlockStats])

  const categories = useMemo(() => {
    const set = new Set<string>()
    catalog.forEach((m) => {
      if (m.category) set.add(m.category)
    })
    return ["ALL", ...Array.from(set)]
  }, [catalog])

  const filteredCatalog = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    return catalog.filter((item) => {
      const majorName = (item.name_vi || item.name || "").toLowerCase()
      const matchCat =
        selectedCategory === "ALL" || item.category === selectedCategory
      const matchQuery =
        !q ||
        item.major_code.toLowerCase().includes(q) ||
        majorName.includes(q) ||
        (item.category && item.category.toLowerCase().includes(q))
      return matchCat && matchQuery
    })
  }, [catalog, searchQuery, selectedCategory])

  const visibleCatalog = showAllCatalog
    ? filteredCatalog
    : filteredCatalog.slice(0, 9)

  const handleExportPdf = () => {
    window.print()
  }

  const handleRetakeAssessment = () => {
    reset()
    navigate("/assessment")
  }

  const handleSelectHistory = (attemptId: string) => {
    selectHistoryAttempt(attemptId)
    setShowHistoryDrawer(false)
    reportTopRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const displayName = user?.name || data?.user_name || "Học sinh"
  const activeAttemptIndex = useMemo(() => {
    if (!activeHistoryId) return 0
    const idx = history.findIndex((h) => h.id === activeHistoryId)
    return idx >= 0 ? idx : 0
  }, [history, activeHistoryId])
  const activeAttempt = history[activeAttemptIndex] || null

  return (
    <section className="py-9 sm:py-12" ref={reportTopRef}>
      <PageContainer>
        {/* Header */}
        <div className="mb-8 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-sky-600">
              <Sparkles size={14} />
              AI CareerGuide · 435 Ngành
            </div>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">
              {hasCompletedAssessment
                ? `Chào ${displayName}, đề xuất ngành của bạn.`
                : `Chào ${displayName}, khám phá bản thân.`}
            </h1>
          </div>

          {hasCompletedAssessment && (
            <div className="flex flex-wrap items-center gap-2.5">
              {history.length > 0 && (
                <Button
                  variant="secondary"
                  icon={History}
                  onClick={() => setShowHistoryDrawer((v) => !v)}
                >
                  Lịch sử ({history.length})
                </Button>
              )}
              <Button
                variant="secondary"
                icon={RotateCcw}
                onClick={handleRetakeAssessment}
              >
                Làm lại
              </Button>
              <Button
                variant="secondary"
                icon={Download}
                onClick={handleExportPdf}
              >
                Xuất PDF
              </Button>
            </div>
          )}
        </div>

        {/* Liquid Glass Empty State when Student has NOT completed the Assessment */}
        {!hasCompletedAssessment ? (
          <div className="relative mb-10 overflow-hidden rounded-[36px] border border-white/80 bg-white/40 p-8 shadow-[0_24px_80px_rgba(14,165,233,0.14)] backdrop-blur-2xl sm:p-14">
            <div className="pointer-events-none absolute -left-16 -top-16 size-72 rounded-full bg-sky-300/35 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-20 -right-16 size-80 rounded-full bg-cyan-200/40 blur-3xl" />

            <div className="relative mx-auto max-w-2xl text-center">
              <span className="mx-auto inline-flex items-center gap-2 rounded-full border border-white/80 bg-white/60 px-4 py-1.5 text-xs font-extrabold tracking-wide text-sky-700 shadow-2xs backdrop-blur-md">
                <ClipboardCheck size={14} />
                Chưa có dữ liệu trắc nghiệm
              </span>

              <h2 className="mt-5 text-2xl font-black tracking-tight text-slate-900 sm:text-3xl">
                Làm bài đánh giá để mở khóa đề xuất từ 435 ngành
              </h2>

              <div className="mt-8 grid gap-4 sm:grid-cols-3">
                {[
                  { weight: "45%", title: "Sở thích RIASEC" },
                  { weight: "35%", title: "Học lực Z-Score" },
                  { weight: "20%", title: "Nhận thức" },
                ].map((pillar) => (
                  <div
                    key={pillar.title}
                    className="rounded-3xl border border-white/80 bg-white/50 p-5 text-center shadow-[0_8px_30px_rgba(14,165,233,0.07)] backdrop-blur-xl"
                  >
                    <p className="text-2xl font-black text-sky-600">
                      {pillar.weight}
                    </p>
                    <h3 className="mt-1 text-sm font-extrabold text-slate-900">
                      {pillar.title}
                    </h3>
                  </div>
                ))}
              </div>

              <div className="mt-9 flex justify-center">
                <Link to="/assessment">
                  <Button
                    icon={ArrowRight}
                    className="rounded-2xl px-8 py-3.5 text-sm shadow-lg shadow-sky-500/20"
                  >
                    Bắt đầu đánh giá ngay
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Collapsible History Drawer (only visible when user clicks "Lịch sử" or has multiple attempts) */}
            {(showHistoryDrawer || history.length > 1) && (
              <div className="mb-6 rounded-3xl border border-white/80 bg-white/50 p-4 shadow-[0_10px_35px_rgba(14,165,233,0.08)] backdrop-blur-xl">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5 text-xs font-bold text-slate-800">
                    <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-sky-500/15 text-sky-600">
                      <Clock size={15} />
                    </span>
                    <span>
                      Lần #{history.length - activeAttemptIndex}
                      <span className="ml-2 font-medium text-slate-400">
                        {formatDateTimeVi(
                          activeAttempt?.createdAt || assessment.completedAt,
                        )}
                      </span>
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-1.5">
                    {history.map((item, idx) => {
                      const isCurrent =
                        item.id === (activeAttempt?.id || history[0]?.id)
                      const attemptNumber = history.length - idx
                      return (
                        <div key={item.id} className="inline-flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => handleSelectHistory(item.id)}
                            className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-bold transition ${
                              isCurrent
                                ? "bg-sky-600 text-white shadow-xs"
                                : "border border-white/80 bg-white/60 text-slate-600 hover:bg-white hover:text-sky-700"
                            }`}
                          >
                            {isCurrent ? <CheckCircle2 size={12} /> : <Eye size={12} />}
                            Lần #{attemptNumber} · {item.topMajorName} ({item.topMatchScore}%)
                          </button>
                          {history.length > 1 && (
                            <button
                              type="button"
                              onClick={() => deleteHistoryAttempt(item.id)}
                              className="rounded-lg p-1.5 text-slate-400 hover:bg-white/70 hover:text-slate-700"
                              title="Xóa"
                            >
                              <Trash2 size={12} />
                            </button>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* Clean 2-Column Layout: Single Left Profile Card + Right 2-Tier Funnel */}
            <div className="grid gap-6 lg:grid-cols-[.82fr_1.18fr]">
              {/* Left Column: Single Unified Profile Card */}
              <div>
                <Card className="rounded-3xl p-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-[11px] font-extrabold uppercase tracking-widest text-sky-600">
                        Hồ sơ RIASEC
                      </p>
                      <h2 className="mt-1 text-xl font-black text-slate-900">
                        {archetypeTitle}
                      </h2>
                    </div>
                    <Badge tone="indigo">{hollandCodeBadge}</Badge>
                  </div>

                  <RiasecRadarChart data={displayedRiasec} />

                  <div className="mt-2 grid grid-cols-3 gap-2">
                    {top3Dimensions.map((item) => (
                      <div
                        className="rounded-2xl border border-white/80 bg-white/55 p-3 text-center backdrop-blur-md"
                        key={item.key}
                      >
                        <p className="text-base font-black text-sky-600">
                          {item.key}
                        </p>
                        <p className="text-[11px] font-semibold text-slate-500">
                          {item.label}
                        </p>
                        <p className="mt-1 text-sm font-black text-slate-900">
                          {item.value}%
                        </p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 flex items-center justify-between rounded-2xl border border-white/80 bg-white/55 px-4 py-3 backdrop-blur-md">
                    <div className="flex items-center gap-2.5">
                      <GraduationCap size={17} className="text-sky-600" />
                      <span className="text-xs font-extrabold text-slate-800">
                        {bestBlockStats.block}
                      </span>
                    </div>
                    <span className="text-xs font-extrabold text-sky-700">
                      Z-Score {bestBlockStats.zScore} · {bestBlockStats.percentile}
                    </span>
                  </div>
                </Card>
              </div>

              {/* Right Column: 2-Tier Recommendation Funnel */}
              <div>
                <TwoTierFunnelRecommendation funnelData={displayedFunnel} />
              </div>
            </div>
          </>
        )}

        {/* Full 435 MOET Majors Catalog Explorer Section */}
        <div ref={catalogRef} className="mt-10">
          <Card className="rounded-[32px] p-6 sm:p-8">
            <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
              <div>
                <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-widest text-sky-600">
                  <Compass size={15} />
                  Danh mục chuẩn Bộ GD&ĐT
                </div>
                <h2 className="mt-1 text-xl font-black text-slate-900">
                  Khám phá {catalog.length} ngành đào tạo
                </h2>
              </div>

              <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                <div className="relative">
                  <Search
                    size={15}
                    className="absolute left-3.5 top-3 text-slate-400"
                  />
                  <input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Tìm mã hoặc tên ngành..."
                    className="h-10 w-full rounded-xl border border-white/85 bg-white/65 pl-9 pr-3 text-xs font-semibold outline-none backdrop-blur-md focus:border-sky-400 focus:bg-white sm:w-60"
                  />
                </div>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="h-10 rounded-xl border border-white/85 bg-white/65 px-3 text-xs font-bold text-slate-700 outline-none backdrop-blur-md focus:border-sky-400"
                >
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat === "ALL" ? "Tất cả lĩnh vực" : cat}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {visibleCatalog.map((item) => {
                const blocks = item.subject_blocks || item.blocks || []
                const majorName = item.name_vi || item.name || item.major_code
                return (
                  <Link
                    key={item.major_code}
                    to={`/majors/${item.major_code}`}
                    className="group flex flex-col justify-between rounded-2xl border border-white/80 bg-white/55 p-4 backdrop-blur-md transition hover:-translate-y-0.5 hover:bg-white/80"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="rounded-md bg-sky-500/12 px-2 py-0.5 text-[10px] font-extrabold text-sky-700">
                          Mã {item.major_code}
                        </span>
                        {blocks.length > 0 && (
                          <span className="text-[10px] font-bold text-slate-500">
                            {blocks.slice(0, 3).join(", ")}
                          </span>
                        )}
                      </div>
                      <h3 className="mt-2 text-sm font-extrabold text-slate-900 group-hover:text-sky-700">
                        {majorName}
                      </h3>
                      <p className="mt-0.5 text-[11px] font-medium text-slate-400">
                        {item.category || "Danh mục ngành"}
                      </p>
                    </div>
                    <div className="mt-3 flex items-center justify-between border-t border-slate-200/50 pt-2 text-[11px] font-bold text-sky-600">
                      <span>Chi tiết</span>
                      <ChevronRight
                        size={14}
                        className="transition-transform group-hover:translate-x-0.5"
                      />
                    </div>
                  </Link>
                )
              })}
            </div>

            {filteredCatalog.length > 9 && (
              <div className="mt-5 text-center">
                <button
                  type="button"
                  onClick={() => setShowAllCatalog((v) => !v)}
                  className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-2 text-xs font-extrabold text-sky-700 transition hover:bg-sky-100"
                >
                  {showAllCatalog
                    ? "Thu gọn danh sách"
                    : `Xem tất cả ${filteredCatalog.length} ngành`}
                </button>
              </div>
            )}
          </Card>
        </div>
      </PageContainer>
    </section>
  )
}
