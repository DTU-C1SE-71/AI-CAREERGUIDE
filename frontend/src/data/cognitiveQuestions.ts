export type CognitiveIconName =
  | "Clapperboard"
  | "BookOpen"
  | "Wrench"
  | "MessagesSquare"
  | "Headphones"
  | "Building2"
  | "Compass"
  | "Landmark"
  | "Calculator"
  | "Lightbulb"
  | "Heart"
  | "Scale"
  | "Cpu"
  | "FileSpreadsheet"
  | "Users"
  | "Sprout"
  | "Binary"
  | "MessageCircle"
  | "Palette"
  | "Hand"
  | "ShieldAlert"
  | "Flame"
  | "Brain"
  | "CalendarCheck"
  | "Rocket"
  | "TrendingUp"
  | "HeartHandshake"
  | "Sparkles"
  | "Terminal"
  | "Crown"
  | "PenTool"
  | "ListChecks"

export interface CognitiveOption {
  option_key: string
  trait_code: string
  label: string
  description: string
  icon: CognitiveIconName
}

export interface CognitiveQuestionItem {
  code: string
  dimension?: string
  dimension_badge?: string
  title: string
  subtitle?: string
  options: CognitiveOption[]
}

export const defaultCognitiveQuestions: CognitiveQuestionItem[] = [
  {
    code: "COG_1",
    dimension: "learning_style",
    dimension_badge: "Cách tiếp thu",
    title: "1. Cách tiếp thu kiến thức",
    subtitle:
      "Khi cần học một kiến thức hoàn toàn mới, bạn thấy cách nào giúp mình nhớ nhanh nhất?",
    options: [
      {
        option_key: "A",
        trait_code: "LEARN_VISUAL_SPATIAL",
        label: "Xem hình ảnh & Sơ đồ",
        description: "Học qua sơ đồ tư duy, hình minh họa hoặc video.",
        icon: "Clapperboard",
      },
      {
        option_key: "B",
        trait_code: "LEARN_THEORETICAL_ANALYTICAL",
        label: "Đọc sách & Hiểu bản chất",
        description: "Đọc kỹ tài liệu, phân tích công thức từ gốc.",
        icon: "BookOpen",
      },
      {
        option_key: "C",
        trait_code: "LEARN_HANDS_ON_PRACTICAL",
        label: "Tự tay thực hành ngay",
        description: "Bắt tay làm thử bài tập, thí nghiệm hoặc thực tế.",
        icon: "Wrench",
      },
      {
        option_key: "D",
        trait_code: "LEARN_INTERACTIVE_CASE",
        label: "Thảo luận cùng mọi người",
        description: "Trao đổi nhóm và giải các tình huống thực tế.",
        icon: "MessagesSquare",
      },
    ],
  },
  {
    code: "COG_2",
    dimension: "work_environment",
    dimension_badge: "Môi trường làm việc",
    title: "2. Không gian làm việc",
    subtitle:
      "Không gian làm việc nào giúp bạn cảm thấy thoải mái và tập trung nhất mỗi ngày?",
    options: [
      {
        option_key: "A",
        trait_code: "ENV_LAB_DIGITAL_QUIET",
        label: "Góc làm việc yên tĩnh",
        description: "Phòng lab hoặc bàn làm việc tập trung sâu.",
        icon: "Headphones",
      },
      {
        option_key: "B",
        trait_code: "ENV_DYNAMIC_CORPORATE",
        label: "Văn phòng mở năng động",
        description: "Thường xuyên gặp gỡ khách hàng, đối tác.",
        icon: "Building2",
      },
      {
        option_key: "C",
        trait_code: "ENV_FIELD_INDUSTRIAL",
        label: "Công trường & Thực địa",
        description: "Di chuyển tại nhà máy, công trình hoặc ngoài trời.",
        icon: "Compass",
      },
      {
        option_key: "D",
        trait_code: "ENV_INSTITUTIONAL_SERVICE",
        label: "Trường học, Bệnh viện & Cơ quan",
        description: "Môi trường chuyên môn cao và giàu tính phục vụ.",
        icon: "Landmark",
      },
    ],
  },
  {
    code: "COG_3",
    dimension: "problem_solving",
    dimension_badge: "Giải quyết vấn đề",
    title: "3. Cách xử lý vấn đề",
    subtitle:
      "Khi cả nhóm gặp một rắc rối lớn trước hạn nộp, bạn thường phản ứng thế nào đầu tiên?",
    options: [
      {
        option_key: "A",
        trait_code: "SOLVE_QUANTITATIVE_LOGIC",
        label: "Kiểm tra số liệu & Logic",
        description: "Rà soát từng bước để tìm đúng chỗ sai.",
        icon: "Calculator",
      },
      {
        option_key: "B",
        trait_code: "SOLVE_CREATIVE_DIVERGENT",
        label: "Tìm một hướng đi mới",
        description: "Đề xuất ý tưởng sáng tạo và khác biệt.",
        icon: "Lightbulb",
      },
      {
        option_key: "C",
        trait_code: "SOLVE_HUMAN_EMPATHY",
        label: "Lắng nghe mọi người trước",
        description: "Hỏi thăm tâm lý và nhu cầu của từng thành viên.",
        icon: "Heart",
      },
      {
        option_key: "D",
        trait_code: "SOLVE_PROCEDURAL_STRATEGIC",
        label: "Xem lại quy định & Chi phí",
        description: "Chọn phương án an toàn, đúng luật và tiết kiệm.",
        icon: "Scale",
      },
    ],
  },
  {
    code: "COG_4",
    dimension: "interaction_target",
    dimension_badge: "Đối tượng công việc",
    title: "4. Đối tượng gắn bó chính",
    subtitle:
      "Trong công việc hàng ngày, bạn thích tiếp xúc nhiều nhất với điều gì?",
    options: [
      {
        option_key: "A",
        trait_code: "TARGET_SYSTEMS_MACHINES",
        label: "Máy móc, Phần mềm & Kỹ thuật",
        description: "Làm việc với code, thiết bị, robot hoặc bản vẽ.",
        icon: "Cpu",
      },
      {
        option_key: "B",
        trait_code: "TARGET_DATA_FINANCE_LAW",
        label: "Số liệu, Tài chính & Văn bản",
        description: "Xử lý bảng thống kê, dòng tiền hoặc hợp đồng.",
        icon: "FileSpreadsheet",
      },
      {
        option_key: "C",
        trait_code: "TARGET_PEOPLE_COMMUNITY",
        label: "Con người & Cộng đồng",
        description: "Giảng dạy, chăm sóc sức khỏe hoặc tư vấn.",
        icon: "Users",
      },
      {
        option_key: "D",
        trait_code: "TARGET_NATURE_BIO_ART",
        label: "Thiên nhiên, Sinh học & Nghệ thuật",
        description: "Nghiên cứu sinh vật, môi trường hoặc sáng tác.",
        icon: "Sprout",
      },
    ],
  },
  {
    code: "COG_5",
    dimension: "gardner_intelligence",
    dimension_badge: "Thế mạnh bản thân",
    title: "5. Điểm mạnh tự nhiên",
    subtitle:
      "Điểm mạnh tự nhiên nào ở trường giúp bạn tự tin nhất khi học tập?",
    options: [
      {
        option_key: "A",
        trait_code: "GARDNER_LOGICAL_MATH",
        label: "Tư duy Toán & Logic",
        description: "Nhạy với con số, công thức và suy luận chặt chẽ.",
        icon: "Binary",
      },
      {
        option_key: "B",
        trait_code: "GARDNER_LINGUISTIC_INTERPERSONAL",
        label: "Ngôn ngữ & Giao tiếp",
        description: "Diễn đạt mạch lạc, giỏi ngoại ngữ và hiểu người khác.",
        icon: "MessageCircle",
      },
      {
        option_key: "C",
        trait_code: "GARDNER_SPATIAL_MUSICAL",
        label: "Hình ảnh, Màu sắc & Âm nhạc",
        description: "Tưởng tượng không gian tốt, có gu thẩm mỹ.",
        icon: "Palette",
      },
      {
        option_key: "D",
        trait_code: "GARDNER_NATURALIST_KINESTHETIC",
        label: "Quan sát tự nhiên & Khéo tay",
        description: "Tinh ý với sinh học hoặc thao tác tay chuẩn xác.",
        icon: "Hand",
      },
    ],
  },
  {
    code: "COG_6",
    dimension: "pressure_tolerance",
    dimension_badge: "Đối mặt áp lực",
    title: "6. Khả năng chịu áp lực",
    subtitle:
      "Với áp lực trong nghề nghiệp, kiểu thử thách nào bạn thấy mình phù hợp nhất?",
    options: [
      {
        option_key: "A",
        trait_code: "PRESSURE_HIGH_STAKES_VITAL",
        label: "Tình huống khẩn cấp & An toàn",
        description: "Giữ bình tĩnh cao trong y tế, an ninh hoặc vận hành.",
        icon: "ShieldAlert",
      },
      {
        option_key: "B",
        trait_code: "PRESSURE_MARKET_DEADLINE",
        label: "Mục tiêu doanh số & Thời hạn gấp",
        description: "Quen với nhịp độ nhanh, sự kiện và cạnh tranh.",
        icon: "Flame",
      },
      {
        option_key: "C",
        trait_code: "PRESSURE_DEEP_RND_COMPLEXITY",
        label: "Bài toán kỹ thuật chuyên sâu",
        description: "Kiên trì nghiên cứu, sửa lỗi hoặc làm đồ án khó.",
        icon: "Brain",
      },
      {
        option_key: "D",
        trait_code: "PRESSURE_STABLE_SUSTAINABLE",
        label: "Nhịp độ ổn định, có kế hoạch",
        description: "Làm việc theo lộ trình rõ ràng và bền vững.",
        icon: "CalendarCheck",
      },
    ],
  },
  {
    code: "COG_7",
    dimension: "output_preference",
    dimension_badge: "Động lực nghề nghiệp",
    title: "7. Thành quả tự hào",
    subtitle:
      "Khi hoàn thành một dự án dài, thành quả nào khiến bạn cảm thấy tự hào nhất?",
    options: [
      {
        option_key: "A",
        trait_code: "OUTPUT_TANGIBLE_TECH_SYSTEM",
        label: "Sản phẩm & Công trình thực tế",
        description: "Ứng dụng chạy tốt, thiết bị hoặc công trình hữu hình.",
        icon: "Rocket",
      },
      {
        option_key: "B",
        trait_code: "OUTPUT_ECONOMIC_LEGAL_VALUE",
        label: "Giá trị kinh tế & Thương vụ",
        description: "Doanh thu tăng trưởng hoặc hợp đồng thành công.",
        icon: "TrendingUp",
      },
      {
        option_key: "C",
        trait_code: "OUTPUT_HUMAN_WELLBEING",
        label: "Sức khỏe & Sự tiến bộ của mọi người",
        description: "Giúp học sinh giỏi hơn, bệnh nhân khỏe mạnh hơn.",
        icon: "HeartHandshake",
      },
      {
        option_key: "D",
        trait_code: "OUTPUT_CREATIVE_SCIENTIFIC_WORK",
        label: "Tác phẩm sáng tạo & Nghiên cứu",
        description: "Sản phẩm nghệ thuật, truyền thông hoặc phát minh.",
        icon: "Sparkles",
      },
    ],
  },
  {
    code: "COG_8",
    dimension: "team_role",
    dimension_badge: "Vai trò trong nhóm",
    title: "8. Vị trí khi làm việc nhóm",
    subtitle:
      "Khi làm bài tập nhóm ở lớp, bạn thường đảm nhận vị trí nào tự nhiên nhất?",
    options: [
      {
        option_key: "A",
        trait_code: "ROLE_TECHNICAL_SPECIALIST",
        label: "Phụ trách phần chuyên môn khó",
        description: "Giải quyết các phần kỹ thuật hoặc tính toán sâu.",
        icon: "Terminal",
      },
      {
        option_key: "B",
        trait_code: "ROLE_STRATEGIC_LEADER",
        label: "Điều phối & Thuyết trình chính",
        description: "Lên kế hoạch, chia việc và trình bày trước lớp.",
        icon: "Crown",
      },
      {
        option_key: "C",
        trait_code: "ROLE_CREATIVE_COMMUNICATOR",
        label: "Lên ý tưởng & Thiết kế nội dung",
        description: "Sáng tạo nội dung, làm slide đẹp và kết nối nhóm.",
        icon: "PenTool",
      },
      {
        option_key: "D",
        trait_code: "ROLE_QUALITY_CONTROLLER",
        label: "Kiểm tra tiến độ & Soát lỗi",
        description: "Tổng hợp tài liệu, giữ đúng hạn và rà soát chi tiết.",
        icon: "ListChecks",
      },
    ],
  },
]
