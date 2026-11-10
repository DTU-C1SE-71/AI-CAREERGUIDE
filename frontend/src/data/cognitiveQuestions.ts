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
    title: "1. Cách học hiệu quả nhất",
    subtitle:
      "Ngày mai kiểm tra chương mới cực khó, tối nay bạn học thế nào cho vào đầu nhanh nhất?",
    options: [
      {
        option_key: "A",
        trait_code: "LEARN_VISUAL_SPATIAL",
        label: "Vẽ sơ đồ & Xem video",
        description: "Vẽ mindmap, xem video mô phỏng hình ảnh trực quan.",
        icon: "Clapperboard",
      },
      {
        option_key: "B",
        trait_code: "LEARN_THEORETICAL_ANALYTICAL",
        label: "Đọc hiểu gốc rễ",
        description:
          "Đọc kỹ sách giáo khoa, tự chứng minh lại công thức để hiểu bản chất.",
        icon: "BookOpen",
      },
      {
        option_key: "C",
        trait_code: "LEARN_HANDS_ON_PRACTICAL",
        label: "Thực hành làm thử ngay",
        description: "Làm thử bài tập, bấm máy hoặc viết thử/thí nghiệm ngay.",
        icon: "Wrench",
      },
      {
        option_key: "D",
        trait_code: "LEARN_INTERACTIVE_CASE",
        label: "Thảo luận cùng nhóm bạn",
        description:
          "Call nhóm bạn bàn luận, giảng qua giảng lại các tình huống thực tế.",
        icon: "MessagesSquare",
      },
    ],
  },
  {
    code: "COG_2",
    dimension: "work_environment",
    dimension_badge: "Môi trường lý tưởng",
    title: "2. Không gian làm việc yêu thích",
    subtitle:
      "Nếu được chọn \"căn cứ\" đi làm mỗi ngày trong mơ, bạn thấy mình hợp chỗ nào nhất?",
    options: [
      {
        option_key: "A",
        trait_code: "ENV_LAB_DIGITAL_QUIET",
        label: "Phòng Lab & Góc yên tĩnh",
        description:
          "Góc làm việc yên tĩnh, đeo tai nghe tập trung máy tính hoặc phòng thí nghiệm.",
        icon: "Headphones",
      },
      {
        option_key: "B",
        trait_code: "ENV_DYNAMIC_CORPORATE",
        label: "Văn phòng mở sôi nổi",
        description: "Hay đi gặp đối tác, chạy sự kiện & giao tiếp nhiều.",
        icon: "Building2",
      },
      {
        option_key: "C",
        trait_code: "ENV_FIELD_INDUSTRIAL",
        label: "Thực địa & Công trình",
        description:
          "Chạy ngoài thực địa, công trình, nhà máy công nghệ cao hoặc đi hiện trường.",
        icon: "Compass",
      },
      {
        option_key: "D",
        trait_code: "ENV_INSTITUTIONAL_SERVICE",
        label: "Môi trường chuẩn mực",
        description:
          "Nơi giàu tính cống hiến như bệnh viện, trường học, cơ quan luật.",
        icon: "Landmark",
      },
    ],
  },
  {
    code: "COG_3",
    dimension: "problem_solving",
    dimension_badge: "Phản xạ xử lý sự cố",
    title: "3. Cách giải quyết vấn đề",
    subtitle:
      "Khi team gặp một rắc rối lớn sát giờ G, phản xạ đầu tiên của bạn là gì?",
    options: [
      {
        option_key: "A",
        trait_code: "SOLVE_QUANTITATIVE_LOGIC",
        label: "Soi số liệu & Logic",
        description:
          "Gom số liệu, soi lại từng bước xem lỗi logic nằm ở đâu.",
        icon: "Calculator",
      },
      {
        option_key: "B",
        trait_code: "SOLVE_CREATIVE_DIVERGENT",
        label: "Nghĩ hướng \"quay xe\" độc lạ",
        description:
          "Đề xuất một phương án đột phá, giàu tính sáng tạo hơn.",
        icon: "Lightbulb",
      },
      {
        option_key: "C",
        trait_code: "SOLVE_HUMAN_EMPATHY",
        label: "Lắng nghe & Gỡ rối",
        description:
          "Lắng nghe mọi người trước để gỡ rối cảm xúc và nhu cầu từng bên.",
        icon: "Heart",
      },
      {
        option_key: "D",
        trait_code: "SOLVE_PROCEDURAL_STRATEGIC",
        label: "Rà soát quy định & Rủi ro",
        description:
          "Kiểm tra lại quy định, luật chơi và cân đối chi phí – rủi ro an toàn.",
        icon: "Scale",
      },
    ],
  },
  {
    code: "COG_4",
    dimension: "interaction_target",
    dimension_badge: "Đối tượng tương tác",
    title: "4. Thứ muốn gắn bó hàng ngày",
    subtitle:
      "Nếu mỗi ngày đi làm được chọn một \"người bạn đồng hành\" chính, bạn thích làm việc với gì nhất?",
    options: [
      {
        option_key: "A",
        trait_code: "TARGET_SYSTEMS_MACHINES",
        label: "Máy móc, Code & Công trình",
        description:
          "Viết phần mềm, lắp robot, chỉnh vi mạch hoặc dựng kết cấu kỹ thuật.",
        icon: "Cpu",
      },
      {
        option_key: "B",
        trait_code: "TARGET_DATA_FINANCE_LAW",
        label: "Số liệu, Tài chính & Luật",
        description:
          "Làm việc cùng bảng thống kê, dòng tiền, hợp đồng và hồ sơ quy chuẩn.",
        icon: "FileSpreadsheet",
      },
      {
        option_key: "C",
        trait_code: "TARGET_PEOPLE_COMMUNITY",
        label: "Con người & Cộng đồng",
        description:
          "Trực tiếp dạy học, chăm sóc bệnh nhân, tư vấn hoặc kết nối khách hàng.",
        icon: "Users",
      },
      {
        option_key: "D",
        trait_code: "TARGET_NATURE_BIO_ART",
        label: "Sinh vật, Tự nhiên & Nghệ thuật",
        description:
          "Nghiên cứu cây trồng, thí nghiệm sinh học hoặc sáng tác tác phẩm đẹp.",
        icon: "Sprout",
      },
    ],
  },
  {
    code: "COG_5",
    dimension: "gardner_intelligence",
    dimension_badge: "Năng khiếu nổi trội",
    title: "5. Điểm mạnh tự nhiên của bạn",
    subtitle:
      "Ở trường, khả năng tự nhiên nào khiến bạn thấy mình \"bắt nhịp\" nhanh hơn hẳn bạn bè?",
    options: [
      {
        option_key: "A",
        trait_code: "GARDNER_LOGICAL_MATH",
        label: "Nhạy bén Con số & Thuật toán",
        description:
          "Dễ nhìn ra quy luật toán học, cấu trúc logic và suy luận nhân quả.",
        icon: "Binary",
      },
      {
        option_key: "B",
        trait_code: "GARDNER_LINGUISTIC_INTERPERSONAL",
        label: "Hoạt ngôn & Đọc vị tâm lý",
        description:
          "Viết lách mượt, học ngoại ngữ nhanh và khéo thuyết phục người nghe.",
        icon: "MessageCircle",
      },
      {
        option_key: "C",
        trait_code: "GARDNER_SPATIAL_MUSICAL",
        label: "Hình khối 3D, Màu sắc & Nhạc",
        description:
          "Tưởng tượng không gian sắc nét, có gu thẩm mỹ bố cục và nhạy âm thanh.",
        icon: "Palette",
      },
      {
        option_key: "D",
        trait_code: "GARDNER_NATURALIST_KINESTHETIC",
        label: "Quan sát tự nhiên & Khéo tay",
        description:
          "Tinh ý với thế giới sinh vật – môi trường hoặc thao tác tay cực chuẩn.",
        icon: "Hand",
      },
    ],
  },
  {
    code: "COG_6",
    dimension: "pressure_tolerance",
    dimension_badge: "Gu vượt áp lực",
    title: "6. Kiểu thử thách chịu được",
    subtitle:
      "Ngành nào cũng có áp lực riêng, kiểu thử thách nào bạn sẵn sàng \"cân\" để đổi lấy thành tựu?",
    options: [
      {
        option_key: "A",
        trait_code: "PRESSURE_HIGH_STAKES_VITAL",
        label: "Xử lý tình huống khẩn cấp",
        description:
          "Giữ cái đầu lạnh chuẩn xác trong ca y tế, an ninh hoặc điều phối an toàn.",
        icon: "ShieldAlert",
      },
      {
        option_key: "B",
        trait_code: "PRESSURE_MARKET_DEADLINE",
        label: "Đua KPI & Deadline nóng",
        description:
          "Hứng khởi trước áp lực doanh số, cạnh tranh thị trường và sự kiện gấp.",
        icon: "Flame",
      },
      {
        option_key: "C",
        trait_code: "PRESSURE_DEEP_RND_COMPLEXITY",
        label: "Cày sâu bài toán kỹ thuật khó",
        description:
          "Kiên trì nhiều tuần tìm lỗi phần mềm, sửa mạch hoặc làm đồ án phức tạp.",
        icon: "Brain",
      },
      {
        option_key: "D",
        trait_code: "PRESSURE_STABLE_SUSTAINABLE",
        label: "Ổn định, có lộ trình bài bản",
        description:
          "Phát huy tốt nhất trong việc có kế hoạch rõ ràng, chuẩn mực và bền vững.",
        icon: "CalendarCheck",
      },
    ],
  },
  {
    code: "COG_7",
    dimension: "output_preference",
    dimension_badge: "Thành quả tự hào",
    title: "7. Động lực cuối dự án",
    subtitle:
      "Sau một năm làm việc hết mình, kết quả nào khiến bạn muốn chụp ảnh khoe ngay nhất?",
    options: [
      {
        option_key: "A",
        trait_code: "OUTPUT_TANGIBLE_TECH_SYSTEM",
        label: "Sản phẩm Công nghệ & Công trình",
        description:
          "App chạy mượt, robot hoạt động thật hoặc tòa nhà hiện hữu ngoài đời.",
        icon: "Rocket",
      },
      {
        option_key: "B",
        trait_code: "OUTPUT_ECONOMIC_LEGAL_VALUE",
        label: "Tăng trưởng Kinh tế & Thương vụ",
        description:
          "Doanh số bứt phá, ký thành công hợp đồng lớn hoặc thắng vụ tranh tụng.",
        icon: "TrendingUp",
      },
      {
        option_key: "C",
        trait_code: "OUTPUT_HUMAN_WELLBEING",
        label: "Con người khỏe & Tiến bộ hơn",
        description:
          "Học trò trưởng thành, bệnh nhân bình phục hoặc môi trường sống xanh sạch.",
        icon: "HeartHandshake",
      },
      {
        option_key: "D",
        trait_code: "OUTPUT_CREATIVE_SCIENTIFIC_WORK",
        label: "Tác phẩm Sáng tạo & Nghiên cứu",
        description:
          "Bộ nhận diện viral, thước phim chạm cảm xúc hay công trình khoa học mới.",
        icon: "Sparkles",
      },
    ],
  },
  {
    code: "COG_8",
    dimension: "team_role",
    dimension_badge: "Vai trò trong đội",
    title: "8. Vị trí quen thuộc khi làm nhóm",
    subtitle:
      "Vào nhóm làm bài thuyết trình cuối kỳ, bạn thường tự động nhận phần nào?",
    options: [
      {
        option_key: "A",
        trait_code: "ROLE_TECHNICAL_SPECIALIST",
        label: "\"Tay to\" gánh kỹ thuật",
        description:
          "Giải quyết phần kỹ thuật hoặc nội dung khó nhằn nhất.",
        icon: "Terminal",
      },
      {
        option_key: "B",
        trait_code: "ROLE_STRATEGIC_LEADER",
        label: "Đội trưởng điều phối",
        description:
          "Chia việc, chốt kế hoạch và lên bục thuyết trình.",
        icon: "Crown",
      },
      {
        option_key: "C",
        trait_code: "ROLE_CREATIVE_COMMUNICATOR",
        label: "Người lên ý tưởng & Thiết kế",
        description:
          "Nghĩ concept mới, làm slide đẹp & khuấy động cả nhóm.",
        icon: "PenTool",
      },
      {
        option_key: "D",
        trait_code: "ROLE_QUALITY_CONTROLLER",
        label: "Người giữ deadline & Soi lỗi",
        description:
          "Tổng hợp file, canh thời gian và soi kỹ từng lỗi nhỏ trước khi nộp.",
        icon: "ListChecks",
      },
    ],
  },
]
