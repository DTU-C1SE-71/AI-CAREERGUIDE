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
    dimension_badge: "Cách học bài mới",
    title: "1. Cách học bài mới",
    subtitle:
      "Khi học một bài mới khá khó ở trường, cách nào giúp bạn hiểu nhanh và nhớ lâu nhất?",
    options: [
      {
        option_key: "A",
        trait_code: "LEARN_VISUAL_SPATIAL",
        label: "Nhìn hình ảnh, sơ đồ & mô phỏng",
        description:
          "Xem sơ đồ tư duy, hình vẽ minh họa, bản đồ hoặc video mô phỏng trực quan.",
        icon: "Clapperboard",
      },
      {
        option_key: "B",
        trait_code: "LEARN_THEORETICAL_ANALYTICAL",
        label: "Đọc kỹ lý thuyết & tự suy luận gốc rễ",
        description:
          'Tự đọc sách, phân tích từng bước công thức, định lý để hiểu tận gốc "vì sao lại thế".',
        icon: "BookOpen",
      },
      {
        option_key: "C",
        trait_code: "LEARN_HANDS_ON_PRACTICAL",
        label: "Bắt tay làm thử & thực hành trực tiếp",
        description:
          "Phải tự tay làm thí nghiệm, lắp thử mô hình hoặc thao tác thật trên thiết bị mới nhớ chắc.",
        icon: "Wrench",
      },
      {
        option_key: "D",
        trait_code: "LEARN_INTERACTIVE_CASE",
        label: "Thảo luận nhóm & liên hệ ví dụ đời thực",
        description:
          "Cùng bạn bè trao đổi, đặt câu hỏi phản biện và gắn bài học vào các câu chuyện thực tế.",
        icon: "MessagesSquare",
      },
    ],
  },
  {
    code: "COG_2",
    dimension: "work_environment",
    dimension_badge: "Không gian học tập",
    title: "2. Không gian học tập ưa thích",
    subtitle:
      "Không gian học tập hoặc sinh hoạt nào giúp bạn thấy tập trung và có hứng nhất?",
    options: [
      {
        option_key: "A",
        trait_code: "ENV_LAB_DIGITAL_QUIET",
        label: "Góc riêng yên tĩnh cùng máy tính, sách vở",
        description:
          "Không gian tĩnh lặng, ít bị làm phiền để một mình tập trung sâu vào màn hình, bản vẽ hoặc bài vở.",
        icon: "Headphones",
      },
      {
        option_key: "B",
        trait_code: "ENV_DYNAMIC_CORPORATE",
        label: "Không gian sôi nổi, đông người trao đổi",
        description:
          "Nơi nhộn nhịp như buổi họp câu lạc bộ, sự kiện trường lớp, được gặp gỡ và bàn bạc liên tục cùng mọi người.",
        icon: "Building2",
      },
      {
        option_key: "C",
        trait_code: "ENV_FIELD_INDUSTRIAL",
        label: "Phòng thực hành, sân bãi hoặc ngoài trời",
        description:
          "Không thích ngồi lì một chỗ; thích di chuyển ngoài trời, vườn cây hoặc góc thực hành có đồ nghề, dụng cụ.",
        icon: "Compass",
      },
      {
        option_key: "D",
        trait_code: "ENV_INSTITUTIONAL_SERVICE",
        label: "Lớp học, phòng bộ môn có giờ giấc và nề nếp rõ ràng",
        description:
          "Môi trường nghiêm túc, ngăn nắp, có thời khóa biểu ổn định và nội quy trật tự rõ ràng.",
        icon: "Landmark",
      },
    ],
  },
  {
    code: "COG_3",
    dimension: "problem_solving",
    dimension_badge: "Cách gỡ rối",
    title: "3. Cách gỡ rối vấn đề",
    subtitle:
      "Khi nhóm bạn gặp một vấn đề rắc rối trong bài tập lớn hoặc hoạt động lớp, phản xạ đầu tiên của bạn là gì?",
    options: [
      {
        option_key: "A",
        trait_code: "SOLVE_QUANTITATIVE_LOGIC",
        label: "Xét dữ kiện & suy luận nguyên nhân theo logic",
        description:
          "Kiểm tra lại thông tin, con số và suy luận từng bước nguyên nhân - kết quả để tìm đúng chỗ sai.",
        icon: "Calculator",
      },
      {
        option_key: "B",
        trait_code: "SOLVE_CREATIVE_DIVERGENT",
        label: "Nghĩ hướng đi mới lạ, khác hẳn cách cũ",
        description:
          "Phác thảo ngay một ý tưởng sáng tạo, độc đáo chưa ai thử để thiết kế lại cách làm ấn tượng hơn.",
        icon: "Lightbulb",
      },
      {
        option_key: "C",
        trait_code: "SOLVE_HUMAN_EMPATHY",
        label: "Lắng nghe cảm nhận & gắn kết mọi người trước",
        description:
          "Hỏi thăm xem ai đang gặp khó khăn gì, giải tỏa căng thẳng để cả nhóm đồng lòng rồi mới làm tiếp.",
        icon: "Heart",
      },
      {
        option_key: "D",
        trait_code: "SOLVE_PROCEDURAL_STRATEGIC",
        label: "Đối chiếu yêu cầu chung & chọn phương án tối ưu",
        description:
          "Xem lại yêu cầu của thầy cô, thời gian hiện có để thống nhất cách làm chắc chắn, tiết kiệm công sức nhất.",
        icon: "Scale",
      },
    ],
  },
  {
    code: "COG_4",
    dimension: "interaction_target",
    dimension_badge: "Đối tượng ưa thích",
    title: "4. Đối tượng thích tiếp xúc",
    subtitle:
      "Khi tự tìm tòi hoặc tham gia hoạt động ở trường lớp, bạn thích làm việc trực tiếp với nhóm nào nhất?",
    options: [
      {
        option_key: "A",
        trait_code: "TARGET_SYSTEMS_MACHINES",
        label: "Máy tính, công nghệ, đồ kỹ thuật & mô hình",
        description:
          "Mày mò phần mềm, công cụ số, mạch điện hoặc tìm hiểu cấu tạo máy móc, mô hình quanh mình.",
        icon: "Cpu",
      },
      {
        option_key: "B",
        trait_code: "TARGET_DATA_FINANCE_LAW",
        label: "Con số thu chi, bảng kế hoạch & quy tắc, lý lẽ",
        description:
          "Tính toán ngân sách nhóm, lập bảng thống kê, đọc tin tức kinh tế - xã hội hoặc bàn luận đúng sai.",
        icon: "FileSpreadsheet",
      },
      {
        option_key: "C",
        trait_code: "TARGET_PEOPLE_COMMUNITY",
        label: "Bạn bè, thầy cô & mọi người xung quanh",
        description:
          "Trò chuyện, hướng dẫn bài vở, lắng nghe chia sẻ hoặc cùng mọi người làm hoạt động tập thể.",
        icon: "Users",
      },
      {
        option_key: "D",
        trait_code: "TARGET_NATURE_BIO_ART",
        label: "Cây cối, sinh vật tự nhiên hoặc hội họa, nhiếp ảnh",
        description:
          "Chăm sóc cây trồng, vật nuôi, khám phá thiên nhiên hoặc say mê vẽ tranh, chụp ảnh, làm đồ thủ công mỹ thuật.",
        icon: "Sprout",
      },
    ],
  },
  {
    code: "COG_5",
    dimension: "gardner_intelligence",
    dimension_badge: "Điểm mạnh tự nhiên",
    title: "5. Điểm mạnh tự nhiên",
    subtitle:
      "Bạn bè thường nhận xét bạn nhạy bén và làm tốt nhất ở khía cạnh nào?",
    options: [
      {
        option_key: "A",
        trait_code: "GARDNER_LOGICAL_MATH",
        label: "Tính toán nhanh & suy luận chặt chẽ",
        description:
          "Nhạy với con số, bài toán mẹo, tìm quy luật nhanh và nói chuyện có đầu có đuôi rất logic.",
        icon: "Binary",
      },
      {
        option_key: "B",
        trait_code: "GARDNER_LINGUISTIC_INTERPERSONAL",
        label: "Diễn đạt tốt, nhạy ngôn ngữ hoặc tinh ý hiểu lòng người",
        description:
          "Viết lách mạch lạc, nói chuyện cuốn hút, học nhanh ngoại ngữ hoặc dễ nhận ra cảm xúc của bạn bè.",
        icon: "MessageCircle",
      },
      {
        option_key: "C",
        trait_code: "GARDNER_SPATIAL_MUSICAL",
        label: "Mắt thẩm mỹ, tưởng tượng hình khối & cảm nhịp điệu",
        description:
          "Nhớ đường giỏi, dễ hình dung vật thể 3D trong đầu, nhạy với màu sắc đẹp hoặc bắt giai điệu rất nhanh.",
        icon: "Palette",
      },
      {
        option_key: "D",
        trait_code: "GARDNER_NATURALIST_KINESTHETIC",
        label: "Khéo tay, vận động tốt hoặc tinh ý với tự nhiên",
        description:
          "Phản xạ tay chân linh hoạt khi chơi thể thao, làm đồ thủ công khéo léo hoặc hay quan sát cây cối, sinh vật.",
        icon: "Hand",
      },
    ],
  },
  {
    code: "COG_6",
    dimension: "pressure_tolerance",
    dimension_badge: "Đối mặt áp lực",
    title: "6. Kiểu áp lực xử lý tốt nhất",
    subtitle:
      "Khi gặp tình huống căng thẳng trong học tập hoặc hoạt động trường lớp, bạn xử lý tốt nhất ở kiểu áp lực nào?",
    options: [
      {
        option_key: "A",
        trait_code: "PRESSURE_HIGH_STAKES_VITAL",
        label: "Tình huống khẩn cấp cần ứng phó nhanh tại chỗ",
        description:
          "Khi có sự cố đột xuất ở lớp, buổi tập hay sân trường cần người lập tức xử lý để giữ an toàn chung.",
        icon: "ShieldAlert",
      },
      {
        option_key: "B",
        trait_code: "PRESSURE_MARKET_DEADLINE",
        label: "Không khí thi đua sôi nổi, chạy đua với thời gian",
        description:
          "Khi thi đấu đối kháng, tranh tài học thuật hoặc chạy sự kiện gấp rút ở trường, bạn càng hào hứng bứt tốc.",
        icon: "Flame",
      },
      {
        option_key: "C",
        trait_code: "PRESSURE_DEEP_RND_COMPLEXITY",
        label: "Bài toán hay sản phẩm khó phải kiên trì gỡ nhiều ngày",
        description:
          "Sẵn sàng ngồi hàng giờ liền tìm một lỗi sai, giải một câu cực khó hoặc trau chuốt sản phẩm đến cùng.",
        icon: "Brain",
      },
      {
        option_key: "D",
        trait_code: "PRESSURE_STABLE_SUSTAINABLE",
        label: "Nhịp độ đều đặn, chuẩn bị kỹ từ sớm theo kế hoạch",
        description:
          "Không thích nước đến chân mới nhảy; bạn làm tốt nhất khi chia nhỏ việc mỗi ngày một ít, chắc chắn và ổn định.",
        icon: "CalendarCheck",
      },
    ],
  },
  {
    code: "COG_7",
    dimension: "output_preference",
    dimension_badge: "Niềm vui thành quả",
    title: "7. Kết quả mang lại niềm vui lớn nhất",
    subtitle:
      "Sau khi hoàn thành một bài tập lớn hay hoạt động ở trường, kết quả nào làm bạn thấy tự hào nhất?",
    options: [
      {
        option_key: "A",
        trait_code: "OUTPUT_TANGIBLE_TECH_SYSTEM",
        label: "Một sản phẩm hay mô hình chạy được thật sự",
        description:
          "Nhìn thấy trang web/công cụ mình làm chạy mượt, hoặc mô hình, thiết bị cả nhóm lắp ráp hoạt động trơn tru.",
        icon: "Rocket",
      },
      {
        option_key: "B",
        trait_code: "OUTPUT_ECONOMIC_LEGAL_VALUE",
        label: "Đạt thứ hạng cao, thuyết phục thành công hoặc gây quỹ có lãi",
        description:
          "Nhóm giành giải, bảo vệ ý tưởng thuyết phục cả lớp hoặc gian hàng hội chợ thu về khoản lãi ấn tượng.",
        icon: "TrendingUp",
      },
      {
        option_key: "C",
        trait_code: "OUTPUT_HUMAN_WELLBEING",
        label: "Giúp bạn bè tiến bộ hoặc mang lại niềm vui cho mọi người",
        description:
          "Nhìn thấy một người bạn hiểu bài hơn, vui khỏe trở lại hoặc hoạt động của mình giúp ích thiết thực cho tập thể.",
        icon: "HeartHandshake",
      },
      {
        option_key: "D",
        trait_code: "OUTPUT_CREATIVE_SCIENTIFIC_WORK",
        label: "Một tác phẩm đẹp mắt hoặc lời giải, phát hiện mới tâm đắc",
        description:
          "Một bộ ảnh/video ấn tượng, bản thiết kế sáng tạo hoặc tìm ra cách giải hay mà ít ai nghĩ tới.",
        icon: "Sparkles",
      },
    ],
  },
  {
    code: "COG_8",
    dimension: "team_role",
    dimension_badge: "Vai trò trong nhóm",
    title: "8. Vai trò quen thuộc khi làm nhóm",
    subtitle:
      "Khi làm bài tập nhóm ở lớp, bạn thường tự nhiên nhận phần việc nào?",
    options: [
      {
        option_key: "A",
        trait_code: "ROLE_TECHNICAL_SPECIALIST",
        label: "Người đào sâu phần chuyên môn hoặc kỹ thuật riêng",
        description:
          "Nhận phần tính toán sâu, xử lý công cụ/máy tính hoặc nghiên cứu nội dung cốt lõi cần tập trung độc lập.",
        icon: "Terminal",
      },
      {
        option_key: "B",
        trait_code: "ROLE_STRATEGIC_LEADER",
        label: "Nhóm trưởng điều phối chung hoặc đại diện thuyết trình",
        description:
          "Lên khung kế hoạch, phân công nhiệm vụ, giữ tiến độ nhóm hoặc đại diện trình bày, phản biện trước lớp.",
        icon: "Crown",
      },
      {
        option_key: "C",
        trait_code: "ROLE_CREATIVE_COMMUNICATOR",
        label: "Người nghĩ ý tưởng mới, làm slide đẹp hoặc gắn kết nhóm",
        description:
          "Đề xuất cách thể hiện sáng tạo, chăm chút hình ảnh/lời văn trình bày hoặc khuấy động không khí vui vẻ của nhóm.",
        icon: "PenTool",
      },
      {
        option_key: "D",
        trait_code: "ROLE_QUALITY_CONTROLLER",
        label: "Người canh thời hạn, chuẩn bị hậu cần & rà lỗi lần cuối",
        description:
          "Nhắc lịch tiến độ, quản lý quỹ/đồ đạc của nhóm và kiểm tra tỉ mỉ từng chi tiết trước khi nộp bài.",
        icon: "ListChecks",
      },
    ],
  },
]
