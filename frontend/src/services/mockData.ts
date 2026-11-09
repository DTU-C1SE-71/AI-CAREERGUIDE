import type { FunnelRecommendationData, Major } from "../types/major"
import type { RoadmapWeek } from "../types/roadmap"

export interface RiasecRadarPoint {
  key: string
  label: string
  value: number // Điểm sở thích RIASEC (%)
  academicValue: number // Điểm học tập quy đổi (%)
  subjectMapping?: string // Tổ hợp/Môn học đối chiếu
  fullMark: number
}

export const riasecData: RiasecRadarPoint[] = [
  { key: "R", label: "Thực tế", value: 68, academicValue: 78, subjectMapping: "Vật lý & Công nghệ", fullMark: 100 },
  { key: "I", label: "Nghiên cứu", value: 92, academicValue: 88, subjectMapping: "Toán & Tin học", fullMark: 100 },
  { key: "A", label: "Nghệ thuật", value: 64, academicValue: 72, subjectMapping: "Ngữ văn & Mỹ thuật", fullMark: 100 },
  { key: "S", label: "Xã hội", value: 78, academicValue: 85, subjectMapping: "Lịch sử & GDCD", fullMark: 100 },
  { key: "E", label: "Quản lý", value: 72, academicValue: 80, subjectMapping: "Tiếng Anh & Kinh tế", fullMark: 100 },
  { key: "C", label: "Nghiệp vụ", value: 60, academicValue: 82, subjectMapping: "Toán & Tin học", fullMark: 100 },
]

export const majors: Major[] = [
  {
    id: "computer-science",
    code: "7480101",
    name: "Khoa học máy tính",
    category: "Máy tính & Công nghệ thông tin",
    university: "Khối A00, A01 · Chuẩn Bộ GD&ĐT",
    match: 94,
    feasibility: "TARGET",
    fit: { interest: 96, academic: 91, cognitive: 94 },
    explanation:
      "### Vì sao phù hợp?\nBạn có nhóm **Investigative (I)** nổi trội, tư duy phân tích tốt và điểm Toán - Tin nằm trong nhóm xuất sắc (+1.18 Z-Score). Ngành này cân bằng đúng giữa khả năng khám phá, giải quyết vấn đề và nhu cầu phát triển công nghệ cao.",
    gaps: ["Tư duy thuật toán", "Tiếng Anh chuyên ngành", "Kỹ năng làm dự án"],
  },
  {
    id: "software-engineering",
    code: "7480201",
    name: "Kỹ thuật phần mềm",
    category: "Máy tính & Công nghệ thông tin",
    university: "Khối A00, A01 · Chuẩn Bộ GD&ĐT",
    match: 92,
    feasibility: "TARGET",
    fit: { interest: 94, academic: 89, cognitive: 93 },
    explanation:
      "### Khả thi cao và định hướng rõ ràng\nĐiểm học thuật khối A00 rất an toàn so với điểm sàn tham chiếu. Năng lực thực hành kết hợp tư duy hệ thống giúp bạn nhanh chóng làm chủ quy trình phát triển sản phẩm công nghệ.",
    gaps: ["Kiến trúc phần mềm", "Cơ sở dữ liệu", "Lập trình web"],
  },
  {
    id: "data-science",
    code: "7460108",
    name: "Khoa học dữ liệu",
    category: "Máy tính & Công nghệ thông tin",
    university: "Khối A00, A01, D07 · Chuẩn Bộ GD&ĐT",
    match: 89,
    feasibility: "REACH",
    fit: { interest: 92, academic: 84, cognitive: 91 },
    explanation:
      "### Tiềm năng bứt phá lớn\nNăng lực nhận diện quy luật và sự tò mò khoa học là lợi thế lớn. Bạn cần củng cố **xác suất thống kê** và kỹ năng lập trình Python để tăng khả năng cạnh tranh trúng tuyển.",
    gaps: ["Xác suất thống kê", "Python cơ bản", "Trình bày dữ liệu"],
  },
  {
    id: "digital-marketing",
    code: "7340115",
    name: "Marketing số",
    category: "Kinh doanh & Quản lý",
    university: "Khối A01, D01 · Chuẩn Bộ GD&ĐT",
    match: 86,
    feasibility: "TARGET",
    fit: { interest: 88, academic: 82, cognitive: 87 },
    explanation:
      "### Một lựa chọn giàu tính kết nối\nĐiểm **Social (S)** và **Enterprising (E)** tốt cho thấy bạn phù hợp môi trường hợp tác, sáng tạo và ra quyết định dựa trên dữ liệu người dùng.",
    gaps: ["Viết nội dung", "Phân tích hành vi", "Công cụ quảng cáo"],
  },
  {
    id: "e-commerce",
    code: "7340122",
    name: "Thương mại điện tử",
    category: "Kinh doanh & Quản lý",
    university: "Khối A00, D01 · Chuẩn Bộ GD&ĐT",
    match: 84,
    feasibility: "TARGET",
    fit: { interest: 85, academic: 80, cognitive: 86 },
    explanation:
      "Giao thoa hoàn hảo giữa nền tảng công nghệ số và vận hành kinh doanh đa nền tảng hiện đại.",
    gaps: ["Vận hành chuỗi cung ứng", "SEO & Digital Ads", "Tài chính số"],
  },
  {
    id: "automation-tech",
    code: "7510301",
    name: "Công nghệ kỹ thuật điều khiển & Tự động hóa",
    category: "Công nghệ kỹ thuật",
    university: "Khối A00, A01 · Chuẩn Bộ GD&ĐT",
    match: 81,
    feasibility: "TARGET",
    fit: { interest: 83, academic: 82, cognitive: 78 },
    explanation:
      "Thế mạnh ở nhóm **Realistic (R)** và điểm môn Vật lý - Toán tạo bệ phóng vững chắc cho các hệ thống robot và dây chuyền thông minh.",
    gaps: ["Vi điều khiển", "Hệ thống nhúng", "Bản vẽ kỹ thuật"],
  },
]

export const defaultFunnelData: FunnelRecommendationData = {
  tier1_fields: [
    {
      field_name: "Máy tính & Công nghệ thông tin",
      icon: "💻",
      match: 92,
      majors_count: 3,
      majors: [majors[0], majors[1], majors[2]],
    },
    {
      field_name: "Kinh doanh & Quản lý",
      icon: "📊",
      match: 85,
      majors_count: 2,
      majors: [majors[3], majors[4]],
    },
    {
      field_name: "Công nghệ kỹ thuật",
      icon: "⚙️",
      match: 81,
      majors_count: 1,
      majors: [majors[5]],
    },
  ],
  all_majors: majors,
}

export const roadmap: RoadmapWeek[] = [
  {
    id: "week-1",
    week: 1,
    eyebrow: "Nền tảng",
    title: "Khái niệm cốt lõi",
    description: "Hiểu bức tranh ngành và xây nền tư duy.",
    content:
      "## Mục tiêu tuần 1\nNắm các khái niệm nền tảng, thuật ngữ và vai trò nghề nghiệp.\n\n### Tài liệu\n- Tổng quan ngành học\n- Video nhập môn 45 phút\n- Bản đồ nghề nghiệp sau tốt nghiệp",
    tasks: [
      "Đọc tổng quan ngành",
      "Hoàn thành video nhập môn",
      "Ghi lại 5 câu hỏi",
    ],
  },
  {
    id: "week-2",
    week: 2,
    eyebrow: "Thực hành",
    title: "Công cụ & phương pháp",
    description: "Làm quen công cụ được dùng trong môi trường thật.",
    content:
      "## Mục tiêu tuần 2\nBiết cách dùng công cụ để giải một bài toán nhỏ.\n\n- Thiết lập môi trường\n- Thực hành có hướng dẫn\n- Tự đánh giá cuối buổi",
    tasks: [
      "Thiết lập công cụ",
      "Làm 3 bài thực hành",
      "Tổng kết lỗi thường gặp",
    ],
  },
  {
    id: "week-3",
    week: 3,
    eyebrow: "Dự án",
    title: "Tình huống thực tế",
    description: "Áp dụng kiến thức đã học vào một bài tập nhỏ.",
    content:
      "## Mục tiêu tuần 3\nHoàn thành một sản phẩm nhỏ có thể đưa vào hồ sơ năng lực.\n\n- Chọn đề bài phù hợp\n- Triển khai theo từng bước\n- Nhận phản hồi và chỉnh sửa",
    tasks: [
      "Chọn 1 trong 3 đề bài",
      "Lên dàn ý giải pháp",
      "Hoàn thành bản thử nghiệm",
    ],
  },
  {
    id: "week-4",
    week: 4,
    eyebrow: "Đánh giá",
    title: "Tự phản hồi & bước tiếp",
    description: "Nhìn lại trải nghiệm để đưa ra quyết định có cơ sở.",
    content:
      "## Mục tiêu tuần 4\nĐánh giá mức độ yêu thích và năng lực thật sự sau 4 tuần.\n\n- So sánh kỳ vọng với thực tế\n- Trao đổi với cố vấn\n- Quyết định đặt nguyện vọng",
    tasks: [
      "Viết báo cáo tự đánh giá",
      "Đặt lịch trò chuyện với cố vấn",
      "Xác định thứ tự nguyện vọng",
    ],
  },
]
